<template>
	<div v-if="criterion" class="lab-criterion-editor space-y-4 border-t border-outline-gray-2 pt-4 mt-2">
		<FormControl
			v-model="criterion.criterion_name"
			:label="__('Criterion Name')"
			:required="true"
			@input="emit('dirty')"
		/>

		<div class="grid grid-cols-2 gap-3">
			<div class="col-span-2 min-w-0">
				<label class="block text-sm font-medium text-ink-gray-7 mb-1">{{ __('DocType to Check') }}</label>
				<Combobox
					class="w-full"
					:modelValue="criterion.doctype_to_check"
					:query="doctypeQuery"
					:options="doctypeOptions"
					:placeholder="__('e.g. Sales Invoice')"
					@update:query="onDoctypeQuery"
					@update:modelValue="onDoctypeSelect"
				/>
			</div>
			<FormControl
				v-model="criterion.points"
				:label="__('Points')"
				type="number"
				@input="emit('dirty')"
			/>
			<FormControl
				v-model="criterion.comparison_operator"
				:label="__('Comparison')"
				type="select"
				:options="['Exists', 'Equals', 'Contains', 'Greater Than', 'Less Than']"
				@change="emit('dirty')"
			/>
			<div class="col-span-2 min-w-0">
				<label class="block text-sm font-medium text-ink-gray-7 mb-1">{{ __('Field to Check') }}</label>
				<Combobox
					class="w-full"
					:modelValue="criterion.field_to_check"
					:options="fieldOptions"
					:placeholder="__('Leave empty for existence check')"
					@update:modelValue="onFieldSelect"
				/>
			</div>
			<FormControl
				v-if="needsExpectedValue"
				v-model="criterion.expected_value"
				:label="__('Expected Value')"
				:description="__('Required for Equals/Contains/Greater/Less comparisons')"
				class="col-span-2"
				@input="emit('dirty')"
			/>
		</div>

		<div>
			<div class="flex items-center justify-between mb-2">
				<label class="block text-sm font-medium text-ink-gray-7">{{ __('Filters') }}</label>
				<Button size="sm" variant="ghost" @click="addFilter">
					<template #prefix><Plus class="w-3 h-3" /></template>
					{{ __('Add filter') }}
				</Button>
			</div>
			<PlaceholderChips :tokens="CRITERION_TOKENS" class="mb-2" @insert="insertFilterValue" />
			<div v-if="filterRows.length" class="space-y-2">
				<div v-for="(row, i) in filterRows" :key="`filter-${i}-${row.field}`" class="grid grid-cols-[1fr,auto,1fr,auto] gap-2 items-center">
					<Combobox
						class="w-full min-w-0"
						:modelValue="row.field"
						:options="fieldOptions"
						:placeholder="__('Field')"
						@update:modelValue="(v) => onFilterFieldSelect(i, v)"
					/>
					<select
						v-model="row.operator"
						class="rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-2 py-1.5 text-sm"
						@change="syncFilters"
					>
						<option value="=">=</option>
						<option value="!=">!=</option>
						<option value="like">like</option>
						<option value=">">></option>
						<option value="<"><</option>
						<option value="in">in</option>
					</select>
					<input
						v-model="row.value"
						type="text"
						class="rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-2 py-1.5 text-sm font-mono"
						:placeholder="__('Value or {placeholder}')"
						@input="syncFilters"
					/>
					<Button variant="ghost" size="sm" @click="removeFilter(i)">
						<X class="w-3.5 h-3.5" />
					</Button>
				</div>
			</div>
			<p v-else class="text-xs text-ink-gray-5 italic mb-2">{{ __('No filters — all records of this DocType will match') }}</p>
			<div v-if="!filterRows.some((r) => r.field === 'company') || (isItemDoctype && !filterRows.some((r) => r.field === 'item_code'))" class="mt-2 flex flex-wrap gap-2 mb-2">
				<Button
					v-if="!filterRows.some((r) => r.field === 'company')"
					size="sm"
					variant="outline"
					@click="addCompanyFilter"
				>
					{{ __('Add company filter ({company_name})') }}
				</Button>
				<Button
					v-if="isItemDoctype && !filterRows.some((r) => r.field === 'item_code')"
					size="sm"
					variant="outline"
					@click="addPrefixedItemCodeFilter"
				>
					{{ __('Add item_code filter ({company_name}-SUFFIX)') }}
				</Button>
			</div>
			<details>
				<summary class="text-xs text-ink-gray-5 cursor-pointer">{{ __('Advanced: edit JSON') }}</summary>
				<textarea
					:value="criterion.filters"
					rows="3"
					class="mt-1 w-full rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-2 py-1.5 text-xs font-mono"
					@input="onFilterJsonInput"
				/>
			</details>
		</div>

		<FormControl
			v-model="criterion.description"
			:label="__('Description')"
			type="textarea"
			:rows="2"
			@input="emit('dirty')"
		/>
	</div>
</template>

<script setup>
import { Button, Combobox, FormControl, call } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { Plus, X } from 'lucide-vue-next'
import PlaceholderChips from '@/components/Lab/PlaceholderChips.vue'
import { CRITERION_TOKENS } from '@/utils/labTokens'
import { parseFiltersJson, serializeFiltersJson, defaultCompanyFilter, prefixedItemCodeFilter } from '@/utils/labNav'

const props = defineProps({
	criterion: { type: Object, required: true },
	labConnection: { type: String, default: '' },
	externalDoctypes: { type: Array, default: () => [] },
})

const emit = defineEmits(['dirty'])

const doctypeQuery = ref('')
const filterRows = ref([])
const syncingFilters = ref(false)
const doctypeFields = ref([])
let loadFieldsSeq = 0

const needsExpectedValue = computed(() => {
	const op = props.criterion?.comparison_operator
	return op && op !== 'Exists'
})

const isItemDoctype = computed(() =>
	(props.criterion?.doctype_to_check || '').trim().toLowerCase() === 'item'
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

const fieldOptions = computed(() =>
	doctypeFields.value.map((f) => ({
		label: `${f.label} (${f.fieldname})`,
		value: f.fieldname,
	}))
)

function filtersJson(rows = filterRows.value) {
	return serializeFiltersJson(rows)
}

function loadFilters() {
	if (syncingFilters.value) return
	const nextRows = parseFiltersJson(props.criterion?.filters || '')
	if (filtersJson(nextRows) === filtersJson()) return
	syncingFilters.value = true
	filterRows.value = nextRows
	syncingFilters.value = false
}

watch(() => props.criterion?.filters, loadFilters, { immediate: true })

function syncFilters() {
	if (syncingFilters.value) return
	const next = filtersJson()
	if ((props.criterion.filters || '') === next) return
	syncingFilters.value = true
	props.criterion.filters = next
	syncingFilters.value = false
	emit('dirty')
}

function onFilterJsonInput(event) {
	const value = event.target.value
	if ((props.criterion.filters || '') === value) return
	syncingFilters.value = true
	props.criterion.filters = value
	filterRows.value = parseFiltersJson(value)
	syncingFilters.value = false
	emit('dirty')
}

async function loadFields(doctype) {
	const seq = ++loadFieldsSeq
	if (!props.labConnection || !doctype) {
		doctypeFields.value = []
		return
	}
	try {
		const fields = await call('lms.lms.api.get_doctype_fields', {
			lab_connection: props.labConnection,
			doctype,
		})
		if (seq !== loadFieldsSeq) return
		doctypeFields.value = fields || []
	} catch {
		if (seq !== loadFieldsSeq) return
		doctypeFields.value = []
	}
}

function ensureDefaultFilters() {
	if (filterRows.value.length || props.criterion?.filters?.trim()) return
	filterRows.value = defaultCompanyFilter()
	syncFilters()
}

watch(
	() => props.criterion?.doctype_to_check,
	(doctype, prev) => {
		if (doctype && !doctypeQuery.value) doctypeQuery.value = doctype
		loadFields(doctype)
		if (prev !== undefined && doctype && doctype !== prev) ensureDefaultFilters()
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
	if (props.criterion.doctype_to_check === next) {
		doctypeQuery.value = next
		return
	}
	props.criterion.doctype_to_check = next
	if (!props.criterion.criterion_name?.trim()) {
		props.criterion.criterion_name = __('{0} exists').format(next)
	}
	doctypeQuery.value = next
	emit('dirty')
}

function onFieldSelect(value) {
	const next = value || ''
	if ((props.criterion.field_to_check || '') === next) return
	props.criterion.field_to_check = next
	emit('dirty')
}

function onFilterFieldSelect(index, value) {
	const next = value || ''
	if ((filterRows.value[index]?.field || '') === next) return
	filterRows.value[index].field = next
	syncFilters()
}

function addFilter() {
	filterRows.value.push({ field: '', operator: '=', value: '' })
}

function addCompanyFilter() {
	filterRows.value.push(...defaultCompanyFilter())
	syncFilters()
}

function addPrefixedItemCodeFilter() {
	const suffix = window.prompt(
		__('Fixed code suffix after {company_name}- (e.g. KOSZULKA-LOGO-M-001):'),
		'KOSZULKA-LOGO-M-001',
	)
	if (!suffix?.trim()) return
	filterRows.value.push(...prefixedItemCodeFilter(suffix.trim()))
	syncFilters()
}

function removeFilter(i) {
	filterRows.value.splice(i, 1)
	syncFilters()
}

function insertFilterValue(token) {
	const empty = filterRows.value.find((r) => !r.value?.trim())
	if (empty) empty.value = token
	else filterRows.value.push({ field: 'company', operator: '=', value: token })
	syncFilters()
}
</script>
