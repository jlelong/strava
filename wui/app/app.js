// vim: set sw=4 ts=4 sts=4:

// Make the table height responsive
$(function() {
    $(window).on('resize', function() {
        $('.scrollableContainer').height(($(window).height() - 60));
    }).trigger("resize");
});


// Angular stuff
var app = angular.module('StravaViewer', ['ui.bootstrap', 'scrollable-table', 'ngCookies']);
app.controller('StravaController', StravaController);
app.filter('selectActivityTypeFilter', selectActivityTypeFilter);
app.filter('dateRangeFilter', dateRangeFilter);

function dateRangeFilter() {
    // Function called for filtering dates
    // items: list of activities to be filtered
    // startStr: start date as a String
    // endStr: end date as a String
    return function (items, startStr, endStr) {
        var retArray = [];
        if (!startStr && !endStr) {
            return items;
        }

        var startDate = moment(startStr, ["YYYY", "YYYY-MM", "YYYY-MM-DD"], true);
        var endDate = moment(endStr, ["YYYY", "YYYY-MM", "YYYY-MM-DD"], true);
        if (!startDate.isValid()) {
            startDate = moment("2000-01-01", "YYYY-MM-DD");
        }
        if (!endDate.isValid()) {
            endDate = moment();
        } else if (moment(endStr, "YYYY", true).isValid()) {
            // make the date be YYYY-12-31
            endDate.set({ "month": 11, "day": 30 });
        } else if (moment(endStr, "YYYY-MM", true).isValid()) {
            // make the date be the last day of the month
            endDate.add(1, "months");
            endDate.subtract(1, "days");
        }

        angular.forEach(items, function (obj) {
            var runDate = moment(obj.date);
            if (runDate.isSameOrAfter(startDate) && runDate.isSameOrBefore(endDate)) {
                retArray.push(obj);
            }
        });

        return retArray;
    };
}

// Activity selector
var ALL_ACTIVITIES = 1;
var ALL_RIDES = 2;
var MTB_RIDES = 3;
var ROAD_RIDES = 4;
var RUNS = 5;
var HIKES = 6;
var NORDICSKI = 7;


// This filter handles both the activity type and the commute selector
function selectActivityTypeFilter() {
    return function (items, activityTypeId, withCommutes) {
        var retArray = [];
        if (activityTypeId.id == ALL_ACTIVITIES && withCommutes) {
            return items;
        }
        angular.forEach(items, function (obj) {
            // activityTypeId can either be an activity type or a bike type because we use a flat selector
            if (((activityTypeId.id == ALL_ACTIVITIES) || (obj.bike_type == activityTypeId.label || obj.activity_type == activityTypeId.label)) && (withCommutes || !obj.commute)) {
                retArray.push(obj);
            }
        });
        return retArray;
    };
}


function StravaController($cookies, $scope, $window, $http, $timeout) {
    var vm = this;

    // Attributes
    vm.is_premium = false;
    vm.connectLabel = "Connect to Strava";
    vm.update_response = "";
    vm.activities = [];
    vm.gears = [];
    vm.gear_stats = [];
    vm.nTotalItems = -1; // This is a convention to highlight that we have not yet requested the db.
    vm.reverse = false;
    vm.update_in_progress = false;
    vm.searchField = "";
    vm.searchRegex = null;
    vm.profile_picture = "";
    // Default order is by decreasing dates
    vm.predicate = 'date';
    vm.reverse = true;
    vm.speedOrPace = "Speed";
    vm.alternate_tab = null;

    // The labels must match the ones used in stravadb.ActivityTypes
    vm.activityTypes = [
        { 'id': ALL_ACTIVITIES, 'label': 'All' },
        { 'id': ALL_RIDES, 'label': 'Ride' },
        { 'id': MTB_RIDES, 'label': 'MTB' },
        { 'id': ROAD_RIDES, 'label': 'Road' },
        { 'id': HIKES, 'label': 'Hike' },
        { 'id': RUNS, 'label': 'Run' },
        { 'id': NORDICSKI, 'label': 'NordicSki' },
    ];
    vm.activityType = vm.activityTypes[0];
    vm.GEARS = 'Gears'
    vm.ACTIVITIES = 'Activities'
    vm.gears_or_activities = vm.GEARS;

    // Methods
    vm.isConnected = function () { return ($cookies.get('connected') !== undefined); };
    vm.connectOrDisconnect = connectOrDisconnect;
    vm.update_activities = update_activities;
    vm.update_gears = update_gears;
    vm.firstUpdate = firstUpdate;
    vm.update_activity = update_activity;
    vm.delete_activity = delete_activity;
    vm.rebuild_activities = rebuild_activities;
    vm.totals = totals;
    vm.narrowSearch = narrowSearch;
    vm.setSort = setSort;
    vm.sortable = sortable;
    vm.search = { field: getterSetterSearchField };
    vm.updateSelectedActivityType = updateSelectedActivityType;
    vm.getSpeed = function(data) { return data.average_speed; }
    vm.getPace = function(data) { return data.average_pace; }
    vm.getSpeedOrPace = vm.getSpeed;
    vm.alternate_tab = alternate_tab;


    if (!vm.isConnected()) {
        vm.connectLabel = "Connect to Strava";
        vm.profile_picture = "";
    } else {
        vm.connectLabel = "Disconnect";
        $http.get('getAthleteProfile').then(function (response) {
            vm.profile_picture = response.data;
        });
        vm.is_premium = ($cookies.get('is_premium') == 1);
    }

    get_activities();
    get_gears();

    function connectOrDisconnect() {
        if (!vm.isConnected())
            $window.location.href = 'connect';
        else
            $window.location.href = 'disconnect';
    }

    // Set the sorting column
    function setSort(objName) {
        vm.predicate = objName;
        vm.reverse = !vm.reverse;
    }

    // Return the value of the predicate column
    function sortable(predicate) {
        return function (obj) {
            if (predicate == 'moving_time') 
                return moment.duration(obj[predicate]);
            return obj[predicate];
        };
    }

    /// Add a pace field for Hike or Run activities.
    /// The argument is modified inside the function.
    /// @param activities is an array of activities
    function addPacetoActivities(activities) {
        angular.forEach(activities, function (obj) {
            if (obj.activity_type == 'Run' | obj.activity_type == 'Hike' | obj.activity_type == 'NordicSki') {
                if (obj.average_speed > 0) {
                    var pace = 60.0 / obj.average_speed; // pace in minutes
                    var minutes = Math.floor(pace);
                    var seconds = parseInt((pace - minutes) * 60);
                    obj.average_pace = minutes + ":" + ("0" + seconds).slice(-2);
                }
                else
                    obj.average_pace = 0;
            }
        });
    }

    // Update the activities database
    function update_activities() {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.update_response = "Update in progress...";
        $http.get('updateactivities').then(function (response) {
            vm.update_response = "Database successfully updated.";
            addPacetoActivities(response.data);
            vm.activities.push.apply(vm.activities, response.data);
            vm.nTotalItems = vm.activities.length;
        });
    }

    // Update the gears database
    function update_gears() {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.update_response = "Update in progress...";
        $http.get('updategears').then(function (response) {
            vm.update_response = "Database successfully updated.";
        });
    }

    function firstUpdate() {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.nTotalItems = -1;
        vm.update_in_progress = true;
        $http.get('updategears').then(function (response) { });
        $http.get('updateactivities').then(function (response) {
            vm.update_response = "Database successfully updated.";
            addPacetoActivities(response.data);
            vm.activities =  response.data;
            vm.nTotalItems = vm.activities.length;
            vm.update_in_progress = false;
        }, function () {
            vm.update_in_progress = false;
        });
    }

    // Update the local database
    function update_activity(id) {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.update_response = "Update in progress...";
        $http.get('updateactivity', { params: { id: id } }).then(function (response) {
            vm.update_response = "Database successfully updated.";
            addPacetoActivities(response.data);
            for (var i = 0; i < vm.activities.length; i++) {
                if (vm.activities[i].id == id) {
                    vm.activities[i] = response.data[0];
                    break;
                }
            }
        });
    }
    //
    // Update the local database
    function delete_activity(id) {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        if (confirm("Are you sure?")) {
            $http.get('deleteactivity', { params: { id: id } }).then(function (response) {
                vm.update_response = "Activity successfully deleted.";
                for (var i = 0; i < vm.activities.length; i++) {
                    if (vm.activities[i].id == id) {
                        vm.activities.splice(i, 1);
                        break;
                    }
                }
            });
        }
    }

    // Upgrade the local database
    function rebuild_activities() {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to upgrade the local DB.");
            return;
        }
        $http.get('rebuildactivities').then(function (response) {
            vm.update_response = "Database successfully rebuilt.";
            get_activities($http);
        });
    }

    // Get the list of activities.
    function get_activities() {
        $http.get('getRuns').then(function (response) {
            addPacetoActivities(response.data);
            vm.activities = response.data;
            vm.nTotalItems = vm.activities.length;
        });
    }

    // Get the list of gears
    function get_gears() {
        // Make we already the activities list
        if (vm.nTotalItems === -1) {
            get_activities();
        }
        $http.get('getGears').then(function (response) {
            var gears = response.data;
            var stats = {};
            angular.forEach(gears, g => {
                stats[g.name] = {'distance': 0, 'elevation': 0};
            });
            angular.forEach(vm.activities, activity => {
                if (activity.gear_name in stats) {
                    var gear_distance = stats[activity.gear_name]['distance'];
                    var gear_elevation = stats[activity.gear_name]['elevation'];
                    gear_distance += activity.distance;
                    gear_elevation += activity.elevation;
                    stats[activity.gear_name] = {'distance': gear_distance, 'elevation': gear_elevation};
                }
            });
            console.log(stats);
            angular.forEach(Object.keys(stats), g => {
                vm.gears.push({'name': g, 'distance': Math.round(stats[g]['distance']), 'elevation': stats[g]['elevation']});
            });
        });
    }
    // Compute the total distance and elevation.
    // To be called on the filtered list
    function totals(items) {
        var elevation = 0.0;
        var distance = 0.0;
        angular.forEach(items, function (obj) {
            elevation += obj.elevation;
            distance += obj.distance;
        });
        return { 'elevation': elevation, 'distance': distance.toFixed(2) };
    }


    function updateSelectedActivityType() {
        if (vm.activityType.id == HIKES || vm.activityType.id == RUNS || vm.activityType.id == NORDICSKI) {
            vm.speedOrPace = "Pace";
            vm.getSpeedOrPace = vm.getPace;
        } else {
            vm.speedOrPace = "Speed";
            vm.getSpeedOrPace = vm.getSpeed;
        }
    }

    // getterSetterSearchField;
    // We use this getterSetter to compute the regex filter only once and not for every line of the table.
    function getterSetterSearchField(value) {
        if (arguments.length) {
            var folded_value = removeAccents(value);
            vm.searchField = folded_value;
            vm.searchRegex = createRegex(folded_value);
        } else {
            return vm.searchField;
        }
    }

    function narrowSearch(regex) {
        return function (obj) {
            if (!regex)
                return true;
            return (removeAccents([obj.name, obj.location, obj.date, obj.gear_name, obj.description].join(' ')).match(regex) !== null);
        };
    }

    function createRegex(pattern) {
        var regex;
        var tokens = [];
        var tokenElements = [];
        var quoteOpen = false;
        var separator = ' ';
        for (var i = 0; i < pattern.length; ++i) {
            var e = pattern[i];
            if (e == '"' && !quoteOpen) {
                // Entering a block
                quoteOpen = true;
            }
            else if (e == '"' && quoteOpen) {
                // Closing a block
                quoteOpen = false;
                continue;
            }
            else if (e == separator && !quoteOpen) {
                // End of a pattern
                if (tokenElements.length > 0) {
                    tokens.push(tokenElements.join(''));
                    tokenElements = [];
                }
            }
            else {
                if (e == '(' || e == ')') tokenElements.push('\\');
                tokenElements.push(e);
            }
        }
        // Push the last pattern
        if (tokenElements.length > 0) {
            tokens.push(tokenElements.join(''));
        }
        // Handle the logic keyword AND.
        var tokensLogic = [];
        var andOpen = false;
        var cur = "";
        var len = tokens.length;
        for (i = 0; i < len; ++i) {
            if (tokens[i] == "AND") {
                continue;
            }
            if ((i < len - 1 && tokens[i + 1] == "AND") || (i > 1 && tokens[i - 1] == "AND")) {
                cur += '(?=.*' + tokens[i] + ')'; // + '(?=.*' + tokens[i+1] + ').*';
                // tokensLogic.push(cur);
                continue;
            }
            else {
                if (cur) {
                    cur += '.*';
                    tokensLogic.push(cur);
                    cur = "";
                }
                tokensLogic.push(tokens[i]);
            }

        }
        if (cur) {
            cur += '.*';
            tokensLogic.push(cur);
            cur = "";
        }
        var reg = new RegExp(tokensLogic.join("|"), 'gi');
        console.log(reg);
        return reg;
    }

    function alternate_tab() {
        if (vm.gears_or_activities === vm.GEARS) {
            vm.gears_or_activities = vm.ACTIVITIES
        } else {
            vm.gears_or_activities = vm.GEARS
        }
    }
}