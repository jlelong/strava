// vim: set sw=4 ts=4 sts=4:

var app = angular.module('MyStrava', ['ui.bootstrap']);

app.filter('dateRange', function() {
    return function(items, startStr, endStr) {
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

        angular.forEach(items, function(obj){
            var runDate = moment(obj.date);
            if(runDate.isSameOrAfter(startDate) && runDate.isSameOrBefore(endDate)) {
                retArray.push(obj);
            }
        });

        return retArray;
    }
});
app.filter('runType', function() {
    return function(items, runTypeId) {
        var retArray = [];
        if (!runTypeId) {
            return items;
        }
        angular.forEach(items, function(obj){
            // runTypeId can either be an activity type or a bike type because we use a flat selector
            if(obj.bike_type == runTypeId || obj.activity_type == runTypeId) {
                retArray.push(obj); 
            }
        });
        return retArray;
    }
});

// Compute the total distance and elevation.
// To be called on the filtered list
function totals(items) {
    var elevation = 0.;
    var distance = 0.;
    angular.forEach(items, function(obj){
        elevation += obj.elevation;
        distance += obj.distance;
    });
    return {'elevation': elevation, 'distance': distance.toFixed(2)};
}

// Query the data base through a Python script.
function query_data(scope, http) {
    http.get('ajax/getRuns.py').then(function(response){
        scope.list = [];
        angular.forEach(response.data, function(obj) {
            if (obj.activity_type == 'Ride'  |  obj.activity_type == 'Run' | obj.activity_type == 'Hike')
                scope.list.push(obj);
        });
        scope.filteredItems = scope.list.length; //Initially for no filter  
        scope.totalItems = scope.list.length;
    });
}

app.controller('runsCrtl', function ($scope, $http, $timeout) {
    $scope.update_response = "";
    query_data($scope, $http);
    $scope.setPage = function(pageNo) {
        $scope.currentPage = pageNo;
    };
    $scope.filter = function() {
        $timeout(function() { 
            $scope.filteredItems = $scope.filtered.length;
        }, 10);
    };

    // Filter to test search pattern against columns {name, location, date}
    $scope.narrowSearch = function(pattern) {
        return function(obj) {
            if (!pattern)
                return true;
            lpattern = pattern.toLowerCase();
            return (obj.name.toLowerCase().indexOf(lpattern) != -1 ||obj.location.toLowerCase().indexOf(lpattern) != -1 ||obj.date.toLowerCase().indexOf(lpattern) != -1);
        };
    };

    $scope.sort_by = function(predicate) {
        $scope.predicate = predicate;
        $scope.reverse = !$scope.reverse;
    };
    $scope.SetSort = function (objName) {
        $scope.predicate = objName;
        $scope.reverse = !$scope.reverse;
        // angular.forEach($scope.names, function (obj) {
        //   for(var i in obj )
        //   {
        //     if(i == objName && obj[i] != '')
        //       obj[i] =  parseFloat(obj[i]);
        //   }
        // });
    };

    $scope.sortable = function(predicate) {
        return function(obj) {
            if (predicate == 'moving_time') {
                return moment.duration(obj[predicate]);
            }
            else {
                return obj[predicate];
            }
        };
    };

    $scope.update = function() {
        $scope.update_response = "";
        $http.get('ajax/updatelocaldb.py').then(function(response){
            $scope.update_response = "Database successfuly updated.";
            query_data($scope, $http);
        });
    };
    $scope.totals = totals;
});
