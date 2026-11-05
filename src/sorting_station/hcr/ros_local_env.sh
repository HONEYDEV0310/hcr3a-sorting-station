# Sourced after ROS setup. Local DDS connects ROS nodes to the Zenoh bridge.
# Preserve explicit launcher settings; direct script defaults match Domain 77.
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
export CYCLONEDDS_URI="${CYCLONEDDS_URI:-file://$hcr_root/config/cyclonedds_zenoh.xml}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-77}"
export ROS_AUTOMATIC_DISCOVERY_RANGE="${ROS_AUTOMATIC_DISCOVERY_RANGE:-LOCALHOST}"
unset ROS_LOCALHOST_ONLY ROS_DISCOVERY_SERVER
unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE
