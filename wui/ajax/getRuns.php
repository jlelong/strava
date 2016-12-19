<?php
include('../includes/config.php');

// $query="select distinct c.customerName, c.addressLine1, c.city, c.state, c.postalCode, c.country, c.creditLimit from customers c order by c.customerNumber";
$query="select r.id,r.name as run_name,r.location,r.date,s.type as run_type, s.frame_type as run_type_id,r.elevation,r.distance,r.moving_time,r.elapsed_time,s.name as spad_name,r.average_speed,r.max_heartrate,r.average_heartrate,r.suffer_score from Runs r left join Spads s on s.id = r.gear_id order by r.date";
$result = $mysqli->query($query) or die($mysqli->error.__LINE__);

$arr = array();
if($result->num_rows > 0) {
	while($row = $result->fetch_assoc()) {
		$arr[] = $row;	
	}
}
# JSON-encode the response
$json_response = json_encode($arr,JSON_NUMERIC_CHECK);

// # Return the response
echo $json_response;
?>
