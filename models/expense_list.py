from odoo import models, fields, api, _


class ExpenseListForm(models.Model):
    _name = 'expense.list'
    _description = 'Expense List'

    expense_date = fields.Date('Expense Date', required=True)
    purpose = fields.Char(string="Purpose")
    total_expense = fields.Float(string='Total Expense')
    expense_type = fields.Selection([
        ('travel', 'Travel'), ('other', 'Other')
    ], string='Expense Type', required=True)
    mode_of_travelling = fields.Selection([
        ('bus', 'Bus'), ('train', 'Train'), ('car', 'Car'), ('bike', 'Bike'), ('auto', 'Auto'), ('other', 'Other')
    ], string='Mode of Travelling')
    km_travel = fields.Float(string='Km Travel')
    exp_id = fields.Many2one('logic.expenses', string="Expense ID", ondelete='cascade')
    # state = fields.Char(related="exp_id.state")
    from_location = fields.Char(string='From Location')
    destination = fields.Char(string='Destination')
    attach_ticket = fields.Binary(string='Attach Ticket')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'logic.expenses'), ('res_id', 'in', self.exp_id.ids)]
        res['context'] = {
            'default_res_model': 'expense.list',
            'default_res_id': self.id,
            'create': False,
            'edit': False,
        }
        return res