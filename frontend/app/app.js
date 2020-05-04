// vim: set sw=4 ts=4 sts=4:

// Make the table height responsive
$(function() {
    $(window).on('resize', function() {
        $('.scrollableContainer').height(($(window).height() - 60));
    }).trigger("resize");
});


// Angular stuff
var app = angular.module('StravaViewer', ['ui.bootstrap', 'scrollable-table', 'ngCookies','ui.toggle']);
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
    vm.isPremium = false;
    vm.connectLabel = "Connect to Strava";
    vm.updateResponse = "";
    vm.activities = [];
    vm.gears = [];
    vm.gearsDict = {};
    vm.nTotalItems = -1; // This is a convention to highlight that we have not yet requested the db.
    vm.reverse = false;
    vm.updateInProgress = false;
    vm.searchField = "";
    vm.searchRegex = null;
    vm.profilePicture = "";
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
    vm.gearsOrActivities = vm.GEARS;

    // Methods
    vm.isConnected = function () { return ($cookies.get('connected') !== undefined); };
    vm.connectOrDisconnect = connectOrDisconnect;
    vm.updateActivities = updateActivities;
    vm.updateGears = updateGears;
    vm.firstUpdate = firstUpdate;
    vm.updateActivity = updateActivity;
    vm.deleteActivity = deleteActivity;
    vm.rebuildActivities = rebuildActivities;
    vm.computeActivityTotals = computeActivityTotals;
    vm.narrowSearch = narrowSearch;
    vm.setSort = setSort;
    vm.sortable = sortable;
    vm.search = { field: getterSetterSearchField };
    vm.updateSelectedActivityType = updateSelectedActivityType;
    vm.getSpeed = function(data) { return data.average_speed; }
    vm.getPace = function(data) { return data.average_pace; }
    vm.getSpeedOrPace = vm.getSpeed;
    vm.alternateTab = alternateTab;


    if (!vm.isConnected()) {
        vm.connectLabel = "Connect to Strava";
        vm.profilePicture = "";
    } else {
        vm.connectLabel = "Disconnect";
        $http.get('getAthleteProfile').then(function (response) {
            vm.profilePicture = response.data;
        });
        vm.isPremium = ($cookies.get('is_premium') == 1);
    }

    // Load all data and compute the totals
    Promise.all([getActivities(), getGears()]).then(() => updateGearTotals(vm.activities))

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
    function updateActivities() {
        vm.updateResponse = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.updateResponse = "Update in progress...";
        $http.get('updateactivities').then(function (response) {
            vm.updateResponse = "Database successfully updated.";
            addPacetoActivities(response.data);
            updateGearTotals(response.data);
            vm.activities.push.apply(vm.activities, response.data);
            vm.nTotalItems = vm.activities.length;
        });
    }

    // Update the gears database
    function updateGears() {
        vm.updateResponse = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.update_response = "Update in progress...";
        $http.get('updategears').then(function (response) {
            vm.updateResponse = "Database successfully updated.";
            getActivities();
            getGears();
        });
    }

    function firstUpdate() {
        vm.updateResponse = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.nTotalItems = -1;
        vm.updateInProgress = true;
        $http.get('updategears').then(function (response) { });
        $http.get('updateactivities').then(function (response) {
            vm.updateResponse = "Database successfully updated.";
            addPacetoActivities(response.data);
            vm.activities =  response.data;
            vm.nTotalItems = vm.activities.length;
            vm.updateInProgress = false;
        }, function () {
            vm.updateInProgress = false;
        });
    }

    // Update the local database
    function updateActivity(id) {
        vm.updateResponse = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.updateResponse = "Update in progress...";
        $http.get('updateactivity', { params: { activity_id: id } }).then(function (response) {
            vm.updateResponse = "Database successfully updated.";
            const activitiesToRemove = []
            for (var i = 0; i < vm.activities.length; i++) {
                if (vm.activities[i].id == id) {
                    activitiesToRemove.push(vm.activities[i])
                    vm.activities[i] = response.data[0];
                    break;
                }
            }
            addPacetoActivities(response.data);
            updateGearTotals(response.data, activitiesToRemove)
        });
    }
    //
    // Update the local database
    function deleteActivity(id) {
        vm.updateResponse = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        if (confirm("Are you sure?")) {
            $http.get('deleteactivity', { params: { activity_id: id } }).then(function (response) {
                vm.updateResponse = "Activity successfully deleted.";
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
    function rebuildActivities() {
        vm.updateResponse = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to upgrade the local DB.");
            return;
        }
        $http.get('rebuildactivities').then(function (response) {
            vm.updateResponse = "Database successfully rebuilt.";
            getActivities($http);
        });
    }

    // Get the list of activities.
    function getActivities() {
        return $http.get('getRuns').then((response) => {
            addPacetoActivities(response.data);
            vm.activities = response.data;
            vm.nTotalItems = vm.activities.length;
        });
    }

    // Get the list of gears
    function getGears() {
        return $http.get('getGears').then((response) => {
            angular.forEach(response.data, g => {
                vm.gearsDict[g.id] = {'name': g.name, 'type': g.type, 'distance': 0, 'elevation': 0};
            });
        });
    }

    function updateGearTotals(activitiesToAdd, activitiesToRemove=undefined) {
        angular.forEach(activitiesToAdd, activity => {
            if (activity.gear_id in vm.gearsDict) {
                vm.gearsDict[activity.gear_id]['distance'] += activity.distance;
                vm.gearsDict[activity.gear_id]['elevation'] += activity.elevation;
            }
        });
        if (activitiesToRemove) {
            angular.forEach(activitiesToRemove, activity => {
                if (activity.gear_id in vm.gearsDict) {
                    vm.gearsDict[activity.gear_id]['distance'] -= activity.distance;
                    vm.gearsDict[activity.gear_id]['elevation'] -= activity.elevation;
                }
            });
        }
        var gears = [];
        angular.forEach(Object.keys(vm.gearsDict), id => {
            const gear = vm.gearsDict[id];
            gears.push({'name': gear['name'], 'activity_type': gear['type'],'distance': Math.round(gear['distance']), 'elevation': gear['elevation']});
        });
        vm.gears = gears;
    }

    // Compute the total distance and elevation.
    // To be called on the filtered list
    function computeActivityTotals(items) {
        var elevation = 0.0;
        var distance = 0.0;
        angular.forEach(items, obj => {
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
            var foldedValue = removeAccents(value);
            vm.searchField = foldedValue;
            vm.searchRegex = createRegex(foldedValue);
        } else {
            return vm.searchField;
        }
    }

    function narrowSearch(regex) {
        return function (obj) {
            if (!regex)
                return true;
            return (removeAccents([obj.name, obj.location, obj.activity_type, obj.date, obj.gear_name, obj.description].join(' ')).match(regex) !== null);
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

    function alternateTab() {
        if (vm.gearsOrActivities === vm.GEARS) {
            vm.gearsOrActivities = vm.ACTIVITIES
        } else {
            vm.gearsOrActivities = vm.GEARS
        }
    }
}
