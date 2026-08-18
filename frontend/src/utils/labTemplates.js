/** Pre-built lab templates for quick start. */
export const LAB_TEMPLATES = [
	{
		id: 'customer-invoice',
		label: __('Customer + Sales Invoice'),
		description: __('Create a customer and issue a sales invoice'),
		steps: [
			{
				item_type: 'Text',
				title: __('Introduction'),
				instructions: __('In this lab you will create a new customer and issue a sales invoice in the ERP system.'),
			},
			{
				item_type: 'Step',
				title: __('Create Customer'),
				instructions: __('Create a new customer with name **{customer_name}**.\n\nUse the copy chip: +[Customer name]({customer_name})'),
				autocomplete_nav_path: '/app/customer/new-customer-1',
				autocomplete_nav_params: '{"customer_name": "{customer_name}", "customer_group": "{customer_group}", "territory": "{territory}"}',
			},
			{
				item_type: 'Step',
				title: __('Create Sales Invoice'),
				instructions: __('Create a Sales Invoice for customer **{customer_name}** with item **{item_name}**, quantity **{order_qty}**.'),
				autocomplete_nav_path: '/app/sales-invoice/new-sales-invoice-1',
				autocomplete_nav_params: '{"company": "{company_name}", "customer": "{customer_name}"}',
			},
		],
		criteria: [
			{
				criterion_name: __('Customer exists'),
				doctype_to_check: 'Customer',
				comparison_operator: 'Exists',
				field_to_check: '',
				expected_value: '',
				filters: '[["customer_name", "=", "{customer_name}"]]',
				points: 30,
				description: __('Student created the customer with the assigned name'),
			},
			{
				criterion_name: __('Sales Invoice exists'),
				doctype_to_check: 'Sales Invoice',
				comparison_operator: 'Exists',
				field_to_check: '',
				expected_value: '',
				filters: '[["company", "=", "{company_name}"], ["customer", "=", "{customer_name}"]]',
				points: 70,
				description: __('Student created a sales invoice for the customer'),
			},
		],
		passing_percentage: 70,
	},
	{
		id: 'item-stock',
		label: __('Item + Stock Entry'),
		description: __('Create a product and record stock'),
		steps: [
			{
				item_type: 'Step',
				title: __('Create Item'),
				instructions: __('Create a new item:\n- Name: +[Item]({item_name})\n- Code: +[Code]({item_code})\n- Price: {item_price} PLN'),
				autocomplete_nav_path: '/app/item/new-item-1',
				autocomplete_nav_params: '{"item_code": "{item_code}", "item_name": "{item_name}"}',
			},
			{
				item_type: 'Step',
				title: __('Stock Entry'),
				instructions: __('Record a stock receipt for item **{item_code}**, quantity **{order_qty}**.'),
				autocomplete_nav_path: '/app/stock-entry/new-stock-entry-1',
				autocomplete_nav_params: '{"company": "{company_name}"}',
			},
		],
		criteria: [
			{
				criterion_name: __('Item created'),
				doctype_to_check: 'Item',
				comparison_operator: 'Exists',
				filters: '[["item_code", "=", "{item_code}"]]',
				points: 40,
				description: '',
			},
			{
				criterion_name: __('Stock Entry submitted'),
				doctype_to_check: 'Stock Entry',
				comparison_operator: 'Exists',
				filters: '[["company", "=", "{company_name}"]]',
				points: 60,
				description: '',
			},
		],
		passing_percentage: 70,
	},
	{
		id: 'sales-order',
		label: __('Sales Order'),
		description: __('Create a customer and sales order'),
		steps: [
			{
				item_type: 'Step',
				title: __('Create Customer'),
				instructions: __('Create customer **{customer_name}** with NIP **{tax_id}**.'),
				autocomplete_nav_path: '/app/customer/new-customer-1',
				autocomplete_nav_params: '{"customer_name": "{customer_name}"}',
			},
			{
				item_type: 'Step',
				title: __('Create Sales Order'),
				instructions: __('Create a Sales Order for **{customer_name}** with item **{item_name}**, qty **{order_qty}**, discount **{discount_pct}%**.'),
				autocomplete_nav_path: '/app/sales-order/new-sales-order-1',
				autocomplete_nav_params: '{"company": "{company_name}", "customer": "{customer_name}"}',
			},
		],
		criteria: [
			{
				criterion_name: __('Customer exists'),
				doctype_to_check: 'Customer',
				comparison_operator: 'Exists',
				filters: '[["customer_name", "=", "{customer_name}"]]',
				points: 35,
			},
			{
				criterion_name: __('Sales Order exists'),
				doctype_to_check: 'Sales Order',
				comparison_operator: 'Exists',
				filters: '[["company", "=", "{company_name}"], ["customer", "=", "{customer_name}"]]',
				points: 65,
			},
		],
		passing_percentage: 70,
	},
	{
		id: 'product-fg-koszulka',
		label: __('Product FG (session-prefixed code)'),
		description: __('Create a finished product with a code unique per student session'),
		steps: [
			{
				item_type: 'Text',
				title: __('Introduction'),
				instructions: __('Each student gets a unique item code based on their session company. Use the copy chips below.'),
			},
			{
				item_type: 'Step',
				title: __('Create finished product'),
				instructions: __(
					'Go to: **Stock → Item → New**\n\n' +
					'Fill in:\n' +
					'- [ ] Item code: +[Item code]({company_name}-KOSZULKA-LOGO-M-001)\n' +
					'- [ ] Item name: +[Company T-shirt with print – M](Company T-shirt with print – M)\n' +
					'- [ ] Item group: +[Products](Products)\n' +
					'- [ ] Default unit of measure: +[Nos](Nos)\n' +
					'- [ ] Maintain stock: checked\n' +
					'- [ ] Allow sales: checked\n' +
					'- [ ] Allow purchase: unchecked\n\n' +
					'Save the product.',
				),
				autocomplete_nav_path: '/app/item/new-item-1',
				autocomplete_nav_params: '{"item_code": "{company_name}-KOSZULKA-LOGO-M-001", "item_name": "Company T-shirt with print – M", "item_group": "Products", "stock_uom": "Nos"}',
			},
		],
		criteria: [
			{
				criterion_name: __('Finished product created'),
				doctype_to_check: 'Item',
				comparison_operator: 'Exists',
				field_to_check: '',
				expected_value: '',
				filters: '[["item_code", "=", "{company_name}-KOSZULKA-LOGO-M-001"]]',
				points: 100,
				description: __('Student created the finished product with their session-prefixed item code'),
			},
		],
		passing_percentage: 70,
	},
]

export function applyLabTemplate(lab, templateId) {
	const tpl = LAB_TEMPLATES.find((t) => t.id === templateId)
	if (!tpl || !lab) return false

	lab.steps = tpl.steps.map((s) => ({
		doctype: 'LMS Lab Step',
		item_type: s.item_type || 'Step',
		title: s.title,
		instructions: s.instructions,
		autocomplete_nav_path: s.autocomplete_nav_path || '',
		autocomplete_nav_params: s.autocomplete_nav_params || '',
	}))

	lab.evaluation_criteria = tpl.criteria.map((c) => ({
		doctype: 'LMS Lab Evaluation Criterion',
		criterion_name: c.criterion_name,
		doctype_to_check: c.doctype_to_check,
		comparison_operator: c.comparison_operator || 'Exists',
		field_to_check: c.field_to_check || '',
		expected_value: c.expected_value || '',
		filters: c.filters || '',
		points: c.points ?? 10,
		description: c.description || '',
	}))

	if (tpl.passing_percentage != null) lab.passing_percentage = tpl.passing_percentage
	return true
}
