from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class LogicExpenseForm(models.Model):
    _name = 'logic.expenses'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Logic Expenses'

    name = fields.Char(string='Description', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
                                  default=lambda self: self.env.user.employee_id)
    state = fields.Selection([
        ('draft', 'Draft'), ('head_approval', 'Head Approval'), ('hr_approval', 'HR Approval'),
        ('accounts_approval', 'Accounts Approval'), ('register_payment', 'Register Payments'), ('paid', 'Paid'),
        ('cancel', 'Cancelled')
    ], string='State', default='draft', tracking=True)
    expense_type = fields.Selection([
        ('travel', 'Travel'), ('food', 'Food'), ('other', 'Other')
    ], string='Expense Type')
    mode_of_travelling = fields.Selection([
        ('bus', 'Bus'), ('train', 'Train'), ('flight', 'Flight'), ('bike', 'Bike'), ('other', 'Other')
    ], string='Mode of Travelling')
    date = fields.Date(string='Date', default=lambda self: fields.Date.context_today(self))
    # from_location = fields.Char(string='From Location')
    # destination = fields.Char(string='Destination')
    expense_ids = fields.One2many('expense.list', 'exp_id', string="Expenses")
    purpose = fields.Text(string='Purpose')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    description = fields.Text(string='Description')
    payment_date = fields.Date(string='Payment Date')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    attachment_number = fields.Integer(string='Attachment Number', compute='_compute_attachment_number')

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'logic.expenses'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'logic.expenses'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'logic.expenses', 'default_res_id': self.id}
        return res

    def action_get_payment_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'view_mode': 'tree,form',
            'res_model': 'payment.request',
            'domain': [('expense_rec_id', '=', self.id)],
            'context': "{'create': False}"
        }

    def action_submit_to_manager(self):
        for i in self:
            user_id = self.env.user.employee_id.parent_id.user_id.id
            i.activity_schedule('logic_expenses.mail_logic_expenses', user_id=user_id,
                                note=f'{i.employee_id.name} Expense approval request sent; please approve or reject.')
        self.write({'state': 'head_approval'})

    def action_return_to_draft(self):
        self.write({'state': 'draft'})

    def action_head_approval(self):
        if self.employee_id.parent_id.user_id.id == self.env.user.id or self.employee_id.in_charge_id.user_id.id == self.env.user.id:
            activity_id = self.env['mail.activity'].search(
                [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
                    'activity_type_id', '=', self.env.ref('logic_expenses.mail_logic_expenses').id)])
            activity_id.action_feedback(feedback=f'expense request approved.')
            user_id = self.env.ref('logic_base.hr_manager_logic_base').users
            for j in user_id:
                self.activity_schedule('logic_expenses.mail_logic_expenses', user_id=j.id,
                                       note=f'{self.employee_id.name} Expense approval request sent; please approve or reject.')
            self.write({'state': 'hr_approval'})
        else:
            raise ValidationError(_('You are not allowed to approve this expense'))

    def action_reject(self):
        activity_id = self.env['mail.activity'].search(
            [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
                'activity_type_id', '=', self.env.ref('logic_expenses.mail_logic_expenses').id)])
        activity_id.action_feedback(feedback=f'expense request rejected.')
        self.write({'state': 'cancel'})

    def action_hr_approval(self):
        activity_id = self.env['mail.activity'].search(
            [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
                'activity_type_id', '=', self.env.ref('logic_expenses.mail_logic_expenses').id)])
        activity_id.action_feedback(feedback=f'expense request approved.')

        user_id = self.env.ref('logic_base.accounts_logic_base').users
        for j in user_id:
            self.activity_schedule('logic_expenses.mail_logic_expenses', user_id=j.id,
                                   note=f'{self.employee_id.name} Expense approval request sent; please approve or reject.')
        self.write({'state': 'accounts_approval'})

    def action_accounts_approval(self):
        activity_id = self.env['mail.activity'].search(
            [('res_id', '=', self.id), ('user_id', '=', self.env.user.id), (
                'activity_type_id', '=', self.env.ref('logic_expenses.mail_logic_expenses').id)])
        activity_id.action_feedback(feedback=f'expense request approved.')
        self.env['payment.request'].sudo().create({
            'source_type': 'expenses',
            'expense_rec_id': self.id,
            # 'sfc_source': self.sfc_id.id,
            # 'state':'payment_request',
            'amount': self.total_cost,
            'description': self.description,
            'account_name': self.employee_id.name_as_per_bank,
            'account_no': self.employee_id.bank_acc_number,
            'ifsc_code': self.employee_id.ifsc_code,
            'bank_name': self.employee_id.bank_name,
            'bank_branch': self.employee_id.branch_bank,

        })
        self.write({'state': 'register_payment'})

    @api.depends('expense_ids.total_expense')
    def _total_expenses(self):

        total = 0
        for order in self.expense_ids:
            total += order.total_expense
        self.update({
            'total_cost': total,

        })

    total_cost = fields.Float(string='Total Cost', compute='_total_expenses', store=True)


class ExpenseSelection(models.Model):
    _inherit = 'payment.request'

    source_type = fields.Selection(
        selection_add=[('expenses', 'Expenses')], ondelete={'expenses': 'cascade'}, string="Source Type",
    )
    expense_rec_id = fields.Many2one('logic.expenses', string='Expense Source')


class AccountPaymentInheritExpense(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        result = super(AccountPaymentInheritExpense, self).action_post()
        if self.payment_request_id:
            # self.payment_request_id.sudo().write({
            #     'state': 'paid',
            #     'payment_date': datetime.today()
            # })

            if self.payment_request_id.expense_rec_id:
                self.payment_request_id.expense_rec_id.sudo().write({
                    'state': 'paid',
                    'payment_date': datetime.today()
                })

        return result
