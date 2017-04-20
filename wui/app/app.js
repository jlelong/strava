// vim: set sw=4 ts=4 sts=4:

// Make the table height responsive
$(function() {
    $(window).resize(function() {
        $('.scrollableContainer').height(($(window).height() - 60));
    }).resize();
});


// Angular stuff
angular
    .module('MyStrava', ['ui.bootstrap', 'scrollable-table', 'ngCookies'])
    .controller('StravaController', StravaController)
    .filter('selectActivityTypeFilter', selectActivityTypeFilter)
    .filter('dateRangeFilter', dateRangeFilter);

function dateRangeFilter()
{
    // Function called for filtering dates
    // items: list of activities to be filtered
    // startStr: start date as a String
    // endStr: end date as a String
    return function(items, startStr, endStr)
    {
        var retArray = [];
        if (!startStr && !endStr) {
            return items;
        }

        var startDate = moment(startStr, ["YYYY", "YYYY-MM", "YYYY-MM-DD"], true);
        var endDate = moment(endStr, ["YYYY", "YYYY-MM", "YYYY-MM-DD"], true);
        if (! startDate.isValid()) {
            startDate = moment("2000-01-01", "YYYY-MM-DD");
        } 
        if (! endDate.isValid()) {
            endDate = moment();
        } else if (moment(endStr, "YYYY", true).isValid()) {
            // make the date be YYYY-12-31
            endDate.set({"month": 11, "day": 30});
        } else if (moment(endStr, "YYYY-MM", true).isValid()) {
            // make the date be the last day of the month
            endDate.add(1, "months");
            endDate.subtract(1, "days");
        }

        angular.forEach(items, function(obj) {
            var runDate = moment(obj.date);
            if(runDate.isSameOrAfter(startDate) && runDate.isSameOrBefore(endDate)) {
                retArray.push(obj);
            }
        });

        return retArray;
    };
}

// This filter handles both the activity type and the commute selector
function selectActivityTypeFilter() 
{
    return function(items, runTypeId, withCommutes) 
    {
        var retArray = [];
        if (!runTypeId && withCommutes) {
            return items;
        }
        angular.forEach(items, function(obj){
            // runTypeId can either be an activity type or a bike type because we use a flat selector
            if(((!runTypeId) || (obj.bike_type == runTypeId || obj.activity_type == runTypeId)) && (withCommutes || !obj.commute)) {
                retArray.push(obj); 
            }
        });
        return retArray;
    };
}


function StravaController($cookies, $scope, $window, $http, $timeout) 
{
    var vm = this;

    // Attributes
    vm.connectLabel = "Connect to Strava";
    vm.update_response = "";
    vm.list = [];
    vm.nTotalItems = -1; // This is a convention to hightlight that we have not yet requested the db.
    vm.reverse = false;
    vm.update_in_progress = false;
    vm.searchField = "";
    vm.searchRegex = null;
    vm.profile_picture = "";
    // Default order is by decreasing dates
    vm.predicate = 'date';
    vm.reverse = true;

    // Methods
    vm.isConnected = function() { return ($cookies.get('connected') !== undefined); };
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
    vm.search =  { field: getterSetterSearchField };
 

    if (!vm.isConnected()) {
        vm.connectLabel = "Connect to Strava";
        vm.profile_picture = "";
    } else {
        vm.connectLabel = "Disconnect";
        $http.get('getAthleteProfile').then(function(response){
            vm.profile_picture = response.data;
        });
    }

    query_data();

    function connectOrDisconnect() 
    { 
        if (! vm.isConnected())
            $window.location.href = 'connect'; 
        else {
            $window.location.href = 'disconnect'; 
        }
    }
    
    // Set the sorting column
    function setSort(objName) 
    {
        vm.predicate = objName;
        vm.reverse = !vm.reverse;
    }

    // Return the value of the predicate column
    function sortable(predicate) 
    {
        return function(obj) {
            if (predicate == 'moving_time') {
                return moment.duration(obj[predicate]);
            }
            else {
                return obj[predicate];
            }
        };
    }

    // Update the activities database
    function update_activities() 
    {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.update_response = "Update in progress...";
        $http.get('updateactivities').then(function(response){
            vm.update_response = "Database successfuly updated.";
            vm.list.push.apply(vm.list, response.data);
            vm.nTotalItems = vm.list.length;
        });
    }

    // Update the gears database
    function update_gears() 
    {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.update_response = "Update in progress...";
        $http.get('updategears').then(function(response){
            vm.update_response = "Database successfuly updated.";
        });
    }

    function firstUpdate()
    {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        vm.nTotalItems = -1;
        vm.update_in_progress = true;
        $http.get('updategears').then(function(response){ });
        $http.get('updateactivities').then(function(response){
            vm.update_response = "Database successfuly updated.";
            vm.list.push.apply(vm.list, response.data);
            vm.nTotalItems = vm.list.length;
            vm.update_in_progress = false;
        }, function() {
            vm.update_in_progress = false;
        });
    }

    // Update the local database
    function update_activity(id) 
    {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        $http.get('updateactivity', {params: {id: id}}).then(function(response){
            vm.update_response = "Database successfuly updated.";
            for (var i = 0; i < vm.list.length; i++) {
                if (vm.list[i].id == id) {
                    vm.list[i] = response.data[0];
                    break;
                }
            }
        });
    }
    //
    // Update the local database
    function delete_activity(id) 
    {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to update the local DB.");
            return;
        }
        if (confirm("Are you sure?")) {
            $http.get('deleteactivity', {params: {id: id}}).then(function(response){
                vm.update_response = "Activity successfuly deleted.";
                for (var i = 0; i < vm.list.length; i++) {
                    if (vm.list[i].id == id) {
                        vm.list.splice(i, 1);
                        break;
                    }
                }
            });
        }
    }

    // Upgrade the local database
    function rebuild_activities() 
    {
        vm.update_response = "";
        if (!vm.isConnected()) {
            alert("Connect to Strava to upgrade the local DB.");
            return;
        }
        $http.get('rebuildactivities').then(function(response){
            vm.update_response = "Database successfuly rebuilt.";
            query_data($http);
        });
    }

    // Query the data base through a Python script.
    function query_data() 
    {
        $http.get('getRuns').then(function(response){
            vm.list = [];
            angular.forEach(response.data, function(obj) {
                if (obj.activity_type == 'Ride'  |  obj.activity_type == 'Run' | obj.activity_type == 'Hike')
                    vm.list.push(obj);
            });
            vm.nTotalItems = vm.list.length;
        });
    }

    // Compute the total distance and elevation.
    // To be called on the filtered list
    function totals(items) 
    {
        var elevation = 0.0;
        var distance = 0.0;
        angular.forEach(items, function(obj){
            elevation += obj.elevation;
            distance += obj.distance;
        });
        return {'elevation': elevation, 'distance': distance.toFixed(2)};
    }


    // getterSetterSearchField;
    // We use this getterSetter to compute the regex filter only once and not for every line of the table.
    function getterSetterSearchField(value) {
        if (arguments.length) {
            vm.searchField = value;
            vm.searchRegex = createRegex(value);
            console.log(vm.searchRegex);
        } else {
            return vm.searchField;
        }
    }

    function narrowSearch(regex)
    {
        return function(obj) {
            if (!regex)
                return true;
            return ((obj.name + obj.location + obj.date + obj.equipment_name).match(regex) !== null);
            // lpattern = pattern.toLowerCase();^M
            // return (obj.name.toLowerCase().indexOf(lpattern) != -1 ||obj.location.toLowerCase().indexOf(lpattern) != -1 ||obj.date.toLowerCase().indexOf(lpattern) != -1);
        };
    }

    function createRegex(pattern) 
    {
        var regex;
        var tokens = [];
        var tokenElements = [];
        var quoteOpen = false;
        var separator = ' ';
        for (var i = 0; i < pattern.length; ++i) {
            var e = pattern[i];
            if (e == '"' && !quoteOpen) {
                // Etnering a block
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
            if (tokens[i] == "AND"){
                continue;
            }
            if ((i < len - 1 && tokens[i+1] == "AND") || (i > 1 && tokens[i-1] == "AND")) {
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
        return  reg;
    }
}
