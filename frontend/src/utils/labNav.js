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

/** Parse nav params JSON object into key-value rows. Object/array values (e.g. a Seed
 * Record's child-table fields) aren't representable as a single string, so they're left
 * out of the rows rather than stringified to "[object Object]" — see serializeNavParamsJson
 * for how they're preserved when the rows are written back. */
export function parseNavParamsJson(raw) {
	if (!raw?.trim()) return []
	try {
		const parsed = JSON.parse(raw)
		if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return []
		return Object.entries(parsed)
			.filter(([, value]) => value === null || typeof value !== 'object')
			.map(([key, value]) => ({
				key,
				value: value == null ? '' : String(value),
			}))
	} catch {
		return []
	}
}

/** Serialize nav param rows to JSON object string. Any object/array values present in
 * `baseRaw` (not representable as rows, so never shown or edited here) are carried over
 * unchanged so they aren't lost when the scalar rows are saved. */
export function serializeNavParamsJson(rows, baseRaw = '') {
	const preserved = {}
	if (baseRaw?.trim()) {
		try {
			const parsedBase = JSON.parse(baseRaw)
			if (parsedBase && typeof parsedBase === 'object' && !Array.isArray(parsedBase)) {
				for (const [key, value] of Object.entries(parsedBase)) {
					if (value !== null && typeof value === 'object') preserved[key] = value
				}
			}
		} catch {
			// Malformed base JSON — nothing to preserve.
		}
	}
	const valid = (rows || []).filter((r) => r.key?.trim())
	if (!valid.length && !Object.keys(preserved).length) return ''
	const obj = { ...preserved }
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
