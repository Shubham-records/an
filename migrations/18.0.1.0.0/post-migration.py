from odoo import api, SUPERUSER_ID

def migrate(cr, version):
    """
    Update configurations for Odoo 18 compatibility
    """
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Update view_mode references if any actions were defined directly in the database
        actions = env['ir.actions.act_window'].search([
            ('res_model', 'in', ['attendance.device', 'device.user', 'attendance.record', 
                                'fingerprint.template', 'device.command', 'operation.log',
                                'face.template']),
            ('view_mode', 'like', 'tree'),
        ])
        
        for action in actions:
            view_mode = action.view_mode.replace('tree', 'tree')
            action.write({'view_mode': view_mode})
        
        # Log that migration was completed successfully
        env['ir.logging'].create({
            'name': 'an_push_attendance',
            'type': 'server',
            'level': 'info',
            'message': 'Successfully migrated an_push_attendance module to Odoo 18',
            'path': 'migrations/18.0.1.0.0/post-migration.py',
            'func': 'migrate',
            'line': 26,
        })
