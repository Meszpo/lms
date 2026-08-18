/** Convert DocType name to Frappe desk navigation path for a new document. */
export function doctypeToNavPath(doctype) {
	if (!doctype) return ''
	const slug = doctype.trim().toLowerCase().replace(/\s+/g, '-')
	return `/app/${slug}/new-${slug}-1`
}

/** Parse Frappe filter JSON array into visual rows. */
export function parseFiltersJson(raw) {
	if (!raw?.trim()) return []
	try {
		const parsed = JSON.parse(raw)
		if (!Array.isArray(parsed)) return []
		return parsed.map((row) => {
			if (!Array.isArray(row) || row.length < 3) return null
			return { field: String(row[0] || ''), operator: String(row[1] || '='), value: String(row[2] ?? '') }
		}).filter(Boolean)
	} catch {
		return []
	}
}

/** Serialize visual filter rows to Frappe filter JSON. */
export function serializeFiltersJson(rows) {
	const valid = (rows || []).filter((r) => r.field?.trim())
	if (!valid.length) return ''
	return JSON.stringify(valid.map((r) => [r.field.trim(), r.operator || '=', r.value ?? '']))
}

/** Parse nav params JSON object into key-value rows. */
export function parseNavParamsJson(raw) {
	if (!raw?.trim()) return []
	try {
		const parsed = JSON.parse(raw)
		if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return []
		return Object.entries(parsed).map(([key, value]) => ({
			key,
			value: value == null ? '' : String(value),
		}))
	} catch {
		return []
	}
}

/** Serialize nav param rows to JSON object string. */
export function serializeNavParamsJson(rows) {
	const valid = (rows || []).filter((r) => r.key?.trim())
	if (!valid.length) return ''
	const obj = {}
	for (const row of valid) obj[row.key.trim()] = row.value ?? ''
	return JSON.stringify(obj)
}

/** Common nav param presets for a DocType. */
export function defaultNavParamsForDoctype(doctype) {
	const dt = (doctype || '').toLowerCase()
	if (dt.includes('sales invoice') || dt.includes('sales order') || dt.includes('quotation')) {
		return [{ key: 'company', value: '{company_name}' }, { key: 'customer', value: '{customer_name}' }]
	}
	if (dt.includes('customer')) {
		return [{ key: 'customer_name', value: '{customer_name}' }]
	}
	if (dt.includes('item')) {
		return [{ key: 'item_code', value: '{item_code}' }]
	}
	return [{ key: 'company', value: '{company_name}' }]
}

/** Default company filter for evaluation criteria. */
export function defaultCompanyFilter() {
	return [{ field: 'company', operator: '=', value: '{company_name}' }]
}

/** Item filter isolated by session-prefixed item_code (Item has no company field). */
export function prefixedItemCodeFilter(suffix) {
	const s = String(suffix || '').trim().replace(/^-+/, '')
	const value = s ? `{company_name}-${s}` : '{company_name}'
	return [{ field: 'item_code', operator: '=', value }]
}
