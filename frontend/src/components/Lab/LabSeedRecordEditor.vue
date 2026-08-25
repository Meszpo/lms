<template>
	<div v-if="seedRecord" class="lab-seed-record-editor space-y-4 border-t border-outline-gray-2 pt-4 mt-2">
		<div class="grid grid-cols-2 gap-3">
			<FormControl
				v-model="seedRecord.label"
				:label="__('Label')"
				:required="true"
				:description="__('Placeholder key, e.g. existing_customer → {existing_customer}')"
				@input="emit('dirty')"
			/>
			<div class="min-w-0">
				<label class="block text-sm font-medium text-ink-gray-7 mb-1">{{ __('Target DocType') }}</label>
				<Combobox
					class="w-full"
					:modelValue="seedRecord.target_doctype"
					:query="doctypeQuery"
					:options="doctypeOptions"
					:placeholder="__('e.g. Customer')"
					@update:query="onDoctypeQuery"
					@update:modelValue="onDoctypeSelect"
				/>
			</div>
		</div>

		<FormControl
			v-model="seedRecord.description"
			:label="__('Description')"
			type="textarea"
			:rows="2"
			:description="__('What this pre-created record represents for the student')"
			@input="emit('dirty')"
		/>

		<details open>
			<summary class="flex items-center justify-between mb-2 gap-2 cursor-pointer select-none">
				<span class="text-sm font-medium text-ink-gray-7">{{ __('Field Values') }}</span>
			</summary>

			<div class="flex justify-end mb-2">
				<Combobox
					class="w-56"
					:modelValue="null"
					:query="addFieldQuery"
					:options="addFieldOptions"
					:placeholder="__('Add field…')"
					@update:query="(q) => (addFieldQuery = q)"
					@update:modelValue="onAddFieldSelect"
				/>
			</div>

			<PlaceholderChips :tokens="tokens" class="mb-2" @insert="insertValue" />

			<p v-if="loadingFields" class="text-xs text-ink-gray-5 mb-2">{{ __('Loading fields…') }}</p>

			<div v-if="fieldRows.length" class="space-y-2">
				<div
					v-for="(row, i) in fieldRows"
					:key="`${row.key}-${i}`"
					class="grid grid-cols-[1fr,1fr,auto] gap-2 items-start"
				>
					<div class="py-1.5 min-w-0">
						<template v-if="row.meta">
							<div class="text-sm text-ink-gray-8 truncate">
								{{ row.meta.label }}<span v-if="row.meta.reqd" class="text-red-500">*</span>
							</div>
							<div class="text-[10px] text-ink-gray-4 font-mono truncate">{{ row.key }}</div>
						</template>
						<input
							v-else
							v-model="row.key"
							type="text"
							class="w-full rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-2 py-1.5 text-sm font-mono"
							:placeholder="__('fieldname')"
							@input="syncRows"
						/>
					</div>
					<Combobox
						v-if="row.meta?.fieldtype === 'Select'"
						class="w-full min-w-0"
						:modelValue="row.value"
						:options="selectOptionsFor(row)"
						:placeholder="__('Value or {placeholder}')"
						@update:modelValue="(v) => setRowValue(row, v)"
					/>
					<input
						v-else
						v-model="row.value"
						type="text"
						class="w-full min-w-0 rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-2 py-1.5 text-sm font-mono"
						:placeholder="__('Value or {placeholder}')"
						@input="syncRows"
					/>
					<Button variant="ghost" size="sm" @click="removeRow(i)">
						<X class="w-3.5 h-3.5" />
					</Button>
				</div>
			</div>
			<p v-else class="text-xs text-ink-gray-5 italic mb-2">
				{{ __('Select a Target DocType above to load its fields, or paste JSON.') }}
			</p>

			<p v-if="!hasPlaceholder" class="text-xs text-ink-amber-6 mt-2">
				{{ __('At least one value must reference a {placeholder} — otherwise concurrent students would create identical records.') }}
			</p>
		</details>

		<details class="mt-2">
			<summary class="text-xs text-ink-gray-5 cursor-pointer">{{ __('Advanced: edit JSON') }}</summary>
			<textarea
				:value="seedRecord.field_values"
				rows="3"
				class="mt-1 w-full rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-2 py-1.5 text-xs font-mono"
				@input="onJsonInput"
			/>
		</details>
	</div>
</template>

<script setup>
import { Button, Combobox, FormControl, call } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import PlaceholderChips from '@/components/Lab/PlaceholderChips.vue'
import { seedRecordTokens, PLACEHOLDER_RE } from '@/utils/labTokens'
import { parseNavParamsJson, serializeNavParamsJson } from '@/utils/labNav'

const props = defineProps({
	seedRecord: { type: Object, required: true },
	labConnection: { type: String, default: '' },
	externalDoctypes: { type: Array, default: () => [] },
	priorRecords: { type: Array, default: () => [] },
})

const emit = defineEmits(['dirty'])

const doctypeQuery = ref('')
const fieldRows = ref([])
const syncingRows = ref(false)
const doctypeFields = ref([])
const loadingFields = ref(false)
let loadFieldsSeq = 0

const tokens = computed(() => seedRecordTokens(props.priorRecords))

const hasPlaceholder = computed(() =>
	fieldRows.value.some((r) => PLACEHOLDER_RE.test(r.value || ''))
)

const doctypeOptions = computed(() => {
	const opts = (props.externalDoctypes || []).map((name) => ({ label: name, value: name }))
	const q = doctypeQuery.value.trim()
	if (q && !opts.some((o) => o.value.toLowerCase() === q.toLowerCase())) {
		// label must equal value — a decorated label causes an infinite resync loop with
		// doctypeQuery below, freezing the tab.
		opts.unshift({ label: q, value: q })
	}
	return opts
})

function fieldValuesJson(rows = fieldRows.value) {
	return serializeNavParamsJson(rows, props.seedRecord?.field_values || '')
}

function loadRows() {
	if (syncingRows.value) return
	const nextRows = parseNavParamsJson(props.seedRecord?.field_values || '').map((r) => ({ ...r, meta: null }))
	if (fieldValuesJson(nextRows) === fieldValuesJson()) return
	syncingRows.value = true
	fieldRows.value = nextRows
	syncingRows.value = false
	attachMeta()
}

watch(() => props.seedRecord?.field_values, loadRows, { immediate: true })

function syncRows() {
	if (syncingRows.value) return
	const next = fieldValuesJson()
	if ((props.seedRecord.field_values || '') === next) return
	syncingRows.value = true
	props.seedRecord.field_values = next
	syncingRows.value = false
	emit('dirty')
}

function onJsonInput(event) {
	const value = event.target.value
	if ((props.seedRecord.field_values || '') === value) return
	syncingRows.value = true
	props.seedRecord.field_values = value
	fieldRows.value = parseNavParamsJson(value).map((r) => ({ ...r, meta: null }))
	syncingRows.value = false
	attachMeta()
	emit('dirty')
}

function setRowValue(row, value) {
	row.value = value || ''
	syncRows()
}

function attachMeta() {
	const byName = Object.fromEntries(doctypeFields.value.map((f) => [f.fieldname, f]))
	for (const row of fieldRows.value) {
		row.meta = byName[row.key] || null
	}
}

async function loadFields(doctype) {
	const seq = ++loadFieldsSeq
	if (!props.labConnection || !doctype) {
		doctypeFields.value = []
		return
	}
	loadingFields.value = true
	try {
		const fields = await call('lms.lms.api.get_doctype_fields', {
			lab_connection: props.labConnection,
			doctype,
		})
		if (seq !== loadFieldsSeq) return
		// Only feeds the "Add field" picker — rendering a row per field (100+ for Item) froze the page.
		doctypeFields.value = fields || []
		attachMeta()
	} catch {
		if (seq !== loadFieldsSeq) return
		doctypeFields.value = []
	} finally {
		if (seq === loadFieldsSeq) loadingFields.value = false
	}
}

watch(
	() => props.seedRecord?.target_doctype,
	(doctype) => {
		if (doctype && !doctypeQuery.value) doctypeQuery.value = doctype
		loadFields(doctype)
	},
	{ immediate: true }
)

function onDoctypeQuery(q) {
	if (doctypeQuery.value === q) return
	doctypeQuery.value = q
}

function onDoctypeSelect(doctype) {
	if (!doctype) return
	const next = String(doctype)
	if (props.seedRecord.target_doctype === next) {
		doctypeQuery.value = next
		return
	}
	props.seedRecord.target_doctype = next
	doctypeQuery.value = next
	emit('dirty')
}

function selectOptionsFor(row) {
	const options = (row.meta?.options || '')
		.split('\n')
		.map((o) => o.trim())
		.filter(Boolean)
		.map((o) => ({ label: o, value: o }))
	const current = (row.value || '').trim()
	if (current && !options.some((o) => o.value === current)) {
		options.unshift({ label: current, value: current })
	}
	return options
}

const addFieldQuery = ref('')

const addFieldOptions = computed(() => {
	const usedKeys = new Set(fieldRows.value.map((r) => r.key))
	const opts = doctypeFields.value
		.filter((f) => !usedKeys.has(f.fieldname))
		.map((f) => ({ label: `${f.label} (${f.fieldname})`, value: f.fieldname }))
	const q = addFieldQuery.value.trim()
	if (q && !opts.some((o) => o.value.toLowerCase() === q.toLowerCase())) {
		// label === value, see doctypeOptions above — same loop risk.
		opts.unshift({ label: q, value: q })
	}
	return opts
})

function onAddFieldSelect(value) {
	addFieldQuery.value = ''
	if (!value) return
	const fieldname = String(value)
	if (fieldRows.value.some((r) => r.key === fieldname)) return
	const meta = doctypeFields.value.find((f) => f.fieldname === fieldname) || null
	fieldRows.value.push({ key: fieldname, value: '', meta })
}

function removeRow(i) {
	fieldRows.value.splice(i, 1)
	syncRows()
}

function insertValue(token) {
	const empty = fieldRows.value.find((r) => !r.value?.trim())
	if (empty) {
		empty.value = token
	} else {
		fieldRows.value.push({ key: '', value: token, meta: null })
	}
	syncRows()
}
</script>
