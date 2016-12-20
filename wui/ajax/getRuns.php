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
$query="SELECT r.id,r.name AS run_name,r.location,DATE(r.date) AS date,s.type as run_type, s.frame_type AS run_type_id,r.elevation,r.distance,r.moving_time,r.elapsed_time,s.name AS spad_name,r.average_speed,r.max_heartrate,r.average_heartrate,r.suffer_score FROM $ACTIVITIES_TABLE AS r LEFT JOIN $BIKES_TABLE AS s ON s.id = r.gear_id ORDER BY r.date DESC";
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
