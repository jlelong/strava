<?php
$db_ini = parse_ini_file("../includes/setup.ini");
$DB_HOST = 'p:localhost';
$DB_USER = $db_ini['user'];
$DB_NAME = $db_ini['base'];
$DB_PASS = $db_ini['password'];
$ACTIVITIES_TABLE = $db_ini['activities_table'];
$BIKES_TABLE = $db_ini['bikes_table'];
$db = new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME) or die('Erreur de connexion '.mysqli_error($db));

if ($db->connect_errno) {
  echo "Echec lors de la connexion à MySQL : " . $db->connect_error;
}

// $query="select distinct c.customerName, c.addressLine1, c.city, c.state, c.postalCode, c.country, c.creditLimit from customers c order by c.customerNumber";
$query="select r.id,r.name as run_name,r.location,r.date,s.type as run_type, s.frame_type as run_type_id,r.elevation,r.distance,r.moving_time,r.elapsed_time,s.name as spad_name,r.average_speed,r.max_heartrate,r.average_heartrate,r.suffer_score from $ACTIVITIES_TABLE as r left join $BIKES_TABLE as s on s.id = r.gear_id order by r.date";
$result = $db->query($query) or die($db->error.__LINE__);

$arr = array();
if($result->num_rows > 0) {
	while($row = $result->fetch_assoc()) {
		$arr[] = $row;	
	}
}
# JSON-encode the response
$json_response = json_encode($arr,JSON_NUMERIC_CHECK);
$db->close();
// # Return the response
echo $json_response;
?>
