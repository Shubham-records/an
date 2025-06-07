from odoo import http
from odoo.http import request, Response
from datetime import datetime


class PushAttendanceController(http.Controller):

    def _auto_create_device(self, SN):
        """
        Helper method to immediately create and configure a new device
        This happens in real-time during the HTTP handshake, not via cron job
        """
        try:
            # Get default timezone from system using the model method
            default_tz = request.env['attendance.device'].sudo()._get_default_timezone()
            
            # Get a default location or create one if none exists
            location = request.env['hr.work.location'].sudo().search([], limit=1)
            if not location:
                # Create a default location if none exists
                try:
                    location = request.env['hr.work.location'].sudo().create({
                        'name': 'Main Location',
                        'address_id': request.env.company.partner_id.id,
                        'active': True,
                    })
                except Exception as e:
                    # Handle exception but continue
                    pass
            
            # Determine device type based on request path and SN
            device_type = 'zk'  # Default to ZKTeco
            
            # Check URL for ESSL endpoints
            request_path = request.httprequest.path
            if '.aspx' in request_path:
                device_type = 'essl'  # Set as ESSL device if .aspx in URL

            # Serial number check for ESSL
            elif SN and (SN.startswith('BRM') or SN.startswith('ESSL')):
                device_type = 'essl'
            
            # Create new device immediately
            device = request.env['attendance.device'].sudo().create({
                'name': f'Device {SN}',
                'serial_number': SN,
                'device_state': 'draft',
                'location': location.id if location else False,
                'device_time_zone': default_tz,
                'is_auto_created': True,
                'device_type': device_type,
                'last_handshake': datetime.now(),  # Set the handshake time immediately
            })
            
            # Immediately run auto-configuration
            if device:
                device.auto_configure_device(SN)
                
                # Try to send notification to administrators using sudo to avoid permission issues
                try:
                    # Use sudo() to bypass access rights when getting the admin group
                    admin_group = request.env.ref('an_push_attendance.group_attendance_devices_admin', raise_if_not_found=False)
                    if admin_group:
                        # Get admin users with sudo to bypass access rights
                        admin_users = admin_group.sudo().users
                        if admin_users:
                            device_url = f'/web#id={device.id}&model=attendance.device&view_type=form'
                            notification_vals = {
                                'subject': f"New Attendance Device Detected: {SN}",
                                'body_html': f"""
                                    <p>A new attendance device has been automatically registered in the system.</p>
                                    <ul>
                                        <li><strong>Serial Number:</strong> {SN}</li>
                                        <li><strong>Device Type:</strong> {device_type.upper()}</li>
                                        <li><strong>Status:</strong> Draft</li>
                                        <li><strong>Date Detected:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                                    </ul>
                                    <p>Please <a href="{device_url}">click here</a> to view and configure this device.</p>
                                    <p><strong>Note:</strong> The device has been automatically configured and is ready for review.</p>
                                """,
                                'email_from': request.env.company.email or 'noreply@example.com',
                                'email_to': ','.join(user.email for user in admin_users if user.email),
                                'auto_delete': False,
                            }
                            request.env['mail.mail'].sudo().create(notification_vals).send()
                except Exception as e:
                    # If there's an error with notifications, log it but continue
                    import traceback
                    traceback.print_exc()
            
            return device
        except Exception as e:
            # Log the exception for debugging
            import traceback
            traceback.print_exc()
            return False

    @http.route('/iclock/cdata', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def returned_data_from_device(self, SN, **kw):
        method = request.httprequest.method
        table = kw.get('table', None)
        
        # Enhanced logging for debugging


        
        # Log client IP and headers for debugging


        
        try:
            data = request.httprequest.data.decode('utf-8')
        except Exception:
            try:
                data = request.httprequest.data.decode('gb18030')
            except Exception as e:

                data = ""
                


        # Find or create the device
        device = request.env['attendance.device'].sudo().search([('serial_number', '=', SN)], limit=1)
        if not device and method == 'GET':
            try:
                # This is our first contact with this device, try to auto-create it

                device = self._auto_create_device(SN)
                if not device:

                    return request.make_response('Could not create device', headers=[('Content-Type', 'text/plain')])
            except Exception as e:

                return request.make_response('Error creating device', headers=[('Content-Type', 'text/plain')])

        if method == 'GET':
            if device:
                response_value = device.get_response_value()
                headers = [
                    ('Content-Type', 'text/plain'),
                    ('Content-Length', str(len(response_value)))
                ]

                return request.make_response(response_value, headers=headers)
            else:

                return request.make_response('Device not found', headers=[('Content-Type', 'text/plain')])
        else:  # POST method
            if not device:
                # Try to auto-create device for POST requests too

                device = self._auto_create_device(SN)
                if not device:

                    return Response("ERROR=1")
                

            
            # Use device.process_data_from_device directly on the device object, not on the model
            # Ensure device is found and used for processing
            res = device.process_data_from_device(method, SN, data, table)

            return Response(res)
            
    @http.route('/iclock/getrequest', type='http', auth='public', methods=['GET'], csrf=False)
    def getrequest(self, SN, **kw):
        # Enhanced logging for debugging


        
        device = request.env['attendance.device'].sudo().search([('serial_number', '=', SN)], limit=1)
        
        # If device doesn't exist, auto-create it in draft state
        if not device:

            device = self._auto_create_device(SN)
            if not device:

                return Response("ERROR")
        
        if device:
            # Update the last_handshake field with the current timestamp
            device.sudo().write({'last_handshake': datetime.now()})
            command = request.env['device.command'].sudo().search([('device_id', '=', device.id), ('status', '=', 'sent')], order='create_date asc', limit=1)
            if command:
                response = f"C:{command.id}:{command.command}"

                return Response(response)

        return Response("OK")

    @http.route('/iclock/getrequest.aspx', type='http', auth='public', methods=['GET'], csrf=False)
    def getrequest_aspx(self, SN, **kw):
        """Handle ESSL devices that use .aspx extension"""


        
        # Reuse the existing getrequest logic
        return self.getrequest(SN, **kw)

    @http.route('/iclock/devicecmd', type='http', auth='public', methods=['POST'], csrf=False)
    def returned_cmd_from_device(self, SN, **kw):
        # Enhanced logging for debugging


        
        try:
            data = request.httprequest.data.decode('utf-8')
        except Exception:
            try:
                data = request.httprequest.data.decode('gb18030')
            except Exception as e:

                data = ""
                

        
        device = request.env['attendance.device'].sudo().search([('serial_number', '=', SN)], limit=1)
        
        # If device doesn't exist, auto-create it
        if not device:

            device = self._auto_create_device(SN)
            if not device:

                return Response("ERROR")
                
        # We have INFO data from the device, process it directly
        if 'INFO' in data:

            device.process_device_info(data)
        
        # Update command log if exists
        command_log = request.env['device.command'].sudo().search([('device_id', '=', device.id)], order='create_date desc', limit=1)
        if command_log:

            command_log.update_command(data, 'received')
            
        return Response("OK")

    @http.route('/iclock/devicecmd.aspx', type='http', auth='public', methods=['POST'], csrf=False)
    def returned_cmd_from_device_aspx(self, SN, **kw):
        """Handle ESSL devices that use .aspx extension"""


        
        # Reuse the existing devicecmd logic
        return self.returned_cmd_from_device(SN, **kw)

    @http.route('/iclock/cdata.aspx', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def returned_data_from_device_aspx(self, SN, **kw):
        """Handle ESSL devices that use .aspx extension"""


        
        # For ESSL devices, make sure to set device_type to 'essl' if device exists
        device = request.env['attendance.device'].sudo().search([('serial_number', '=', SN)], limit=1)
        if device and device.device_type != 'essl':
            device.write({'device_type': 'essl'})

            
        # Reuse the existing cdata logic
        return self.returned_data_from_device(SN, **kw)
