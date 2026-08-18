/** Session-level placeholders (always available). */
export const SESSION_TOKENS = [
	{ value: '{username}', description: __("Student's login on the external system"), group: 'session', example: 'jan.kowalski' },
	{ value: '{password}', description: __("Student's password on the external system"), group: 'session', example: '••••••' },
	{ value: '{company_name}', description: __('Generated company name for this student (unique per session)'), group: 'session', example: 'LAB-abc123def' },
	{ value: '{url}', description: __('Base URL of the external system'), group: 'session', example: 'https://erp.example.com' },
]

/** Randomized business data generated per lab session. */
export const SESSION_DATA_TOKENS = [
	{ value: '{customer_name}', description: __('Random Polish company name (customer)'), group: 'customer', example: 'Firma ABC Sp. z o.o.' },
	{ value: '{customer_type}', description: __('Customer type: Company or Individual'), group: 'customer', example: 'Company' },
	{ value: '{customer_group}', description: __('Customer group, e.g. Commercial'), group: 'customer', example: 'Commercial' },
	{ value: '{territory}', description: __('Sales territory, e.g. Poland'), group: 'customer', example: 'Poland' },
	{ value: '{tax_id}', description: __('NIP / VAT number'), group: 'customer', example: '1234567890' },
	{ value: '{contact_first}', description: __('Contact person — first name'), group: 'contact', example: 'Anna' },
	{ value: '{contact_last}', description: __('Contact person — last name'), group: 'contact', example: 'Nowak' },
	{ value: '{contact_full}', description: __('Contact person — full name'), group: 'contact', example: 'Anna Nowak' },
	{ value: '{contact_email}', description: __('Contact person — e-mail'), group: 'contact', example: 'anna.nowak@firma.pl' },
	{ value: '{contact_phone}', description: __('Contact person — phone'), group: 'contact', example: '+48 600 123 456' },
	{ value: '{addr_street}', description: __('Address — street line'), group: 'address', example: 'ul. Marszałkowska 10' },
	{ value: '{addr_city}', description: __('Address — city'), group: 'address', example: 'Warszawa' },
	{ value: '{addr_pincode}', description: __('Address — postal code'), group: 'address', example: '00-001' },
	{ value: '{item_name}', description: __('Random product name'), group: 'product', example: 'Laptop Pro 15' },
	{ value: '{item_code}', description: __('Product code (item_name + token)'), group: 'product', example: 'LAPTOP-preview' },
	{ value: '{item_group}', description: __('Product group, e.g. Products'), group: 'product', example: 'Products' },
	{ value: '{item_uom}', description: __('Unit of measure, e.g. Nos'), group: 'product', example: 'Nos' },
	{ value: '{item_price}', description: __('Selling price (PLN)'), group: 'product', example: '2499.00' },
	{ value: '{order_qty}', description: __('Order quantity'), group: 'order', example: '5' },
	{ value: '{discount_pct}', description: __('Discount percentage'), group: 'order', example: '10' },
]

export const TOKEN_GROUPS = [
	{ id: 'session', label: __('Session') },
	{ id: 'customer', label: __('Customer') },
	{ id: 'contact', label: __('Contact') },
	{ id: 'address', label: __('Address') },
	{ id: 'product', label: __('Product') },
	{ id: 'order', label: __('Order') },
]

export const STEP_TOKENS = [...SESSION_TOKENS, ...SESSION_DATA_TOKENS]

export const NAV_TOKENS = [
	{ value: '{company_name}', description: __('Generated company name'), group: 'session' },
	{ value: '{username}', description: __("Student's login"), group: 'session' },
	...SESSION_DATA_TOKENS,
]

export const CRITERION_TOKENS = [
	{ value: '{company_name}', description: __('Generated company name for this student'), group: 'session' },
	{ value: '{username}', description: __("Student's login on the external system"), group: 'session' },
	...SESSION_DATA_TOKENS,
]

/** Sample values for preview mode (matches backend _generate_session_data shape). */
export const PREVIEW_SAMPLE_DATA = {
	username: 'preview.user',
	password: 'preview123',
	company_name: 'Lab_preview_user',
	url: 'https://erp.example.com',
	customer_name: 'Firma Przykładowa Sp. z o.o. [preview]',
	customer_type: 'Company',
	customer_group: 'Commercial',
	territory: 'Poland',
	tax_id: '1234567890',
	contact_first: 'Anna',
	contact_last: 'Nowak',
	contact_full: 'Anna Nowak',
	contact_email: 'anna.nowak@firma.pl',
	contact_phone: '+48 600 123 456',
	addr_street: 'ul. Marszałkowska 10',
	addr_city: 'Warszawa',
	addr_pincode: '00-001',
	item_name: 'Laptop Pro preview',
	item_code: 'LAPTOP-preview',
	item_group: 'Products',
	item_uom: 'Nos',
	item_price: '2499.00',
	order_qty: '5',
	discount_pct: '10',
}

export function resolveLabPlaceholders(text, data = PREVIEW_SAMPLE_DATA) {
	if (!text) return ''
	let out = text
	for (const [key, value] of Object.entries(data)) {
		out = out.replaceAll(`{${key}}`, value == null ? '' : String(value))
	}
	return out
}

/** Build a session-unique code: `{company_name}-SUFFIX` → e.g. `LAB-abc123-KOSZULKA-LOGO-M-001`. */
export function companyPrefixed(suffix) {
	const s = String(suffix || '').trim().replace(/^-+/, '')
	return s ? `{company_name}-${s}` : '{company_name}'
}

/** Copyable chip with a session-prefixed code value. */
export function companyPrefixedChip(label, suffix) {
	const token = companyPrefixed(suffix)
	const display = label?.trim() || suffix
	return `+[${display}](${token})`
}
