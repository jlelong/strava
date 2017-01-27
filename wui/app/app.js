// vim: set sw=4 ts=4 sts=4:

// Make the table height responsive
$(function() {
    $(window).resize(function() {
        $('.scrollableContainer').height(($(window).height() - 260));
    }).resize();
});


// Angular stuff
angular
    .module('MyStrava', ['ui.bootstrap', 'scrollable-table'])
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


function StravaController($scope, $window, $http, $timeout) 
{
    var vm = this;

    // Attributes
    vm.connectLabel = "Connect to Strava";
    vm.update_response = "";
    vm.list = [];
    vm.nTotalItems = 0;
    vm.reverse = false;
    vm.searchField = "";
    vm.searchRegex = null;

    // Methods
    vm.connect = function() { $window.location.href = 'connect'; };
    vm.update = update;
    vm.totals = totals;
    // Filter to test search pattern against columns {name, location, date}
    vm.narrowSearch = narrowSearch;
    vm.setSort = setSort;
    vm.sortable = sortable;
    vm.search =  { field: getterSetterSearchField };
 

    query_data($http);
    
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

    // Update the local database
    function update() 
    {
        vm.update_response = "";
        $http.get('updatelocaldb').then(function(response){
            vm.update_response = "Database successfuly updated.";
            query_data($http);
        });
    }

    // Query the data base through a Python script.
    function query_data(http) 
    {
        http.get('getRuns').then(function(response){
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
            return ((obj.name + obj.location + obj.date).match(regex) !== null);
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
                tokenElements.push(e);
            }
        }
        // Push the last pattern
        if (tokenElements.length > 0) {
            tokens.push(tokenElements.join(''));
        }
        // Handle the logic keyword AND.
        var tokensLogic = [];
        for (i = 0; i < tokens.length; ++i) {
            if (tokens[i] == "AND") {
                var prev = tokensLogic.pop();
                var cur = '(?=.*' + prev + ')' + '(?=.*' + tokens[i+1] + ').*';
                tokensLogic.push(cur);
                ++i;
                continue;
            }
            else {
                tokensLogic.push(tokens[i]);
            }

        }
        return new RegExp(tokensLogic.join("|"), 'gi');
    }


    
}
