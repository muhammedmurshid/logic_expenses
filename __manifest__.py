{
    'name': "Logic Expenses",
    'version': "14.0.1.0",
    'sequence': "0",
    'depends': ['base', 'mail', 'logic_payments', 'account', 'logic_base'],
    'data': [
        'security/ir.model.access.csv',
        'security/user_rules.xml',
        'views/expense_form_view.xml',
        'data/activity.xml',
        'views/cancallation_wizard.xml'

    ],

    'demo': [],
    'summary': "logic_expenses_module",
    'description': "logic_expenses_module",
    'installable': True,
    'auto_install': False,
    'license': "LGPL-3",
    'application': False
}
