// vim: set sw=4 ts=4 sts=4:

var app = angular.module('MyStrava', ['ui.bootstrap']);

app.filter('startFrom', function() {
    return function(input, start) {
        if(input) {
            start = +start; //parse to int
            return input.slice(start);
        }
        return [];
    }
});
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
            console.log(endDate);
            endDate.set({"month": 11, "day": 30});
            console.log(endDate);
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
            if(obj.bike_type == runTypeId) {
                retArray.push(obj); 
            }
        });
        return retArray;
    }
});


function query_data(scope, http) {
    http.get('ajax/getRuns.py').then(function(response){
        scope.list = response.data;
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
    $scope.sort_by = function(predicate) {
        $scope.predicate = predicate;
        $scope.reverse = !$scope.reverse;
    };
    $scope.SetSort = function (objName) {
        $scope.predicate = objName;
        $scope.reverse = !$scope.reverse;
        angular.forEach($scope.names, function (obj) {
          for(var i in obj )
          {
            if(i == objName && obj[i] != '') 
              obj[i] =  parseFloat(obj[i]);       
          }
        });
    };

    $scope.update = function() {
        $scope.update_response = "";
        $http.get('ajax/updatelocaldb.py').then(function(response){
            $scope.update_response = "Database successfuly updated.";
            query_data($scope, $http);
        });
    };
});
