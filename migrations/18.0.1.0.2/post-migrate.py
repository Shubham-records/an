import logging

def migrate(cr, version):
    """
    Fix devices with invalid device_type values
    """
    logger = logging.getLogger(__name__)
    
    # Check if there are any devices with NULL device_type values
    cr.execute("""
        SELECT id, serial_number
        FROM attendance_device
        WHERE device_type IS NULL
    """)
    
    null_devices = cr.fetchall()
    if null_devices:
        logger.info(f"Found {len(null_devices)} devices with NULL device_type")
        
        # Update them to a valid device_type
        for device_id, serial_number in null_devices:
            device_type = 'other'
            
            # Try to determine device type from serial number
            if serial_number and (serial_number.startswith('BRM') or serial_number.startswith('ESSL')):
                device_type = 'essl'
            
            cr.execute("""
                UPDATE attendance_device
                SET device_type = %s
                WHERE id = %s
            """, (device_type, device_id))
            
            logger.info(f"Updated device {device_id} (SN: {serial_number}) to type: {device_type}")
            
    # Check if there are any devices with invalid device_type values
    cr.execute("""
        SELECT id, serial_number, device_type
        FROM attendance_device
        WHERE device_type NOT IN ('zk', 'essl', 'other')
    """)
    
    invalid_devices = cr.fetchall()
    if invalid_devices:
        logger.info(f"Found {len(invalid_devices)} devices with invalid device_type")
        
        # Update them to a valid device_type
        for device_id, serial_number, current_type in invalid_devices:
            device_type = 'other'
            
            # Try to determine device type from serial number
            if serial_number and (serial_number.startswith('BRM') or serial_number.startswith('ESSL')):
                device_type = 'essl'
            
            cr.execute("""
                UPDATE attendance_device
                SET device_type = %s
                WHERE id = %s
            """, (device_type, device_id))
            
            logger.info(f"Updated device {device_id} (SN: {serial_number}) from type: {current_type} to type: {device_type}")
            
    return 