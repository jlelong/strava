var app = angular.module('myApp', ['angularUtils.directives.dirPagination']);

app.controller('runsCtrl', function($scope, $http) {
    $scope.orderByField = 'date';
    $scope.reverseSort = false;
    $scope.currentPage = 1;
    $scope.pageSize = 5;
        $http.get("ajax/getRuns.php")
        .success(function (response) {
            $scope.names = response;
        });
        
    $scope.SetSort = function (objName, isCurrency) {
        $scope.predicate = objName;
        $scope.reverse = !$scope.reverse;
        if(angular.isDefined(isCurrency)) {
            angular.forEach($scope.names, function (obj) {
            for(var i in obj )
            {
               if(i == objName && obj[i] != '') 
                  obj[i] =  parseFloat(obj[i]);       
            }
           });
        }
    }
  
});

