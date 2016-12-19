var app = angular.module('MyStrava', ['ui.bootstrap','daterangepicker']);

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
    return function(items, startDate, endDate) {
        var retArray = [];

        if (!startDate && !endDate) {
            return items;
        }

        angular.forEach(items, function(obj){
            var runDate = obj.date;        
            if(moment(runDate).isAfter(startDate) && moment(runDate).isBefore(endDate)) {
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
            if(obj.run_type_id == runTypeId) {
                retArray.push(obj); 
            }
        });
        return retArray;
    }
});
app.controller('runsCrtl', function ($scope, $http, $timeout) {
    $http.get('ajax/getRuns.php').success(function(data){
        $scope.list = data;
        $scope.currentPage = 1; //current page
        $scope.entryLimit = 100; //max no of items to display in a page
        $scope.filteredItems = $scope.list.length; //Initially for no filter  
        $scope.totalItems = $scope.list.length;
    });
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
});
