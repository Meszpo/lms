<template>
	<div v-if="step" class="space-y-4 border-t border-outline-gray-2 pt-4 mt-2">
		<FormControl
			v-model="step.item_type"
			:label="__('Item Type')"
			type="select"
			:options="[
				{ label: __('Step — numbered task with checkbox'), value: 'Step' },
				{ label: __('Text — free text / section header'), value: 'Text' },
			]"
			@change="emit('dirty')"
		/>
		<FormControl
			v-model="step.title"
			:label="__('Title')"
			:required="true"
			@input="emit('dirty')"
		/>

		<div>
			<label class="block text-sm font-medium text-ink-gray-7 mb-1">{{ __('Instructions') }}</label>
			<div class="mb-2 flex items-center gap-1 rounded-md bg-surface-gray-2 px-2 py-1.5 flex-wrap">
				<button
					v-for="fmt in STEP_FMT_BUTTONS"
					:key="fmt.cmd"
					type="button"
					:title="fmt.title"
					class="px-2 py-0.5 text-xs rounded hover:bg-surface-gray-4 text-ink-gray-7 font-medium transition-colors border border-transparent hover:border-outline-gray-2"
					@mousedown.prevent="applyFormat(fmt.cmd)"
				>{{ fmt.label }}</button>
				<span class="mx-1 text-outline-gray-3 text-xs select-none">|</span>
				<button
					type="button"
					:title="__('Insert copyable code unique per student: {company_name}-SUFFIX')"
					class="px-2 py-0.5 text-xs rounded hover:bg-surface-gray-4 text-ink-gray-7 font-medium transition-colors border border-transparent hover:border-outline-gray-2 whitespace-nowrap"
					@mousedown.prevent="insertPrefixedCodeChip"
				>{{ __('Prefixed code') }}</button>
				<PlaceholderChips :tokens="STEP_TOKENS" @insert="insertToken" />
			</div>
			<div class="mb-2 flex items-start gap-2 rounded-md bg-surface-gray-2 px-3 py-2 text-xs text-ink-gray-6">
				<Info class="size-3.5 shrink-0 mt-0.5 text-ink-gray-4" />
				<span>
					{{ __('Use +[label](value) for copyable chips.') }}
					{{ __('For shared instructions with many concurrent students, use {company_name}-SUFFIX in chips and criteria — each student gets a unique code.') }}
				</span>
			</div>
			<textarea
				ref="instructionsRef"
				v-model="step.instructions"
				rows="8"
				class="w-full rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-outline-blue-3 font-mono"
				:placeholder="__('Describe what the student should do.\nUse +[Copy label](value) to add inline copyable values.')"
				@input="emit('dirty')"
			/>
		</div>

		<!-- Student preview -->
		<div v-if="step.instructions" class="rounded-lg border bg-surface-gray-1 overflow-hidden">
			<div class="px-3 py-1.5 border-b bg-surface-gray-2 text-xs font-medium text-ink-gray-5">
				{{ __('Student preview') }}
			</div>
			<div
				class="px-4 py-3 text-sm instructions-body lab-step-preview"
				v-html="previewHtml"
			/>
		</div>

		<div v-if="step.item_type !== 'Text'" class="border-t pt-4 space-y-3">
			<div class="text-sm font-medium text-ink-gray-7">
				{{ __('Navigation') }}
				<span class="font-normal text-ink-gray-4 text-xs ml-1">{{ __('(optional — opens a pre-filled form in the lab system window)') }}</span>
			</div>

			<div class="grid grid-cols-2 gap-3">
				<div>
					<label class="block text-sm font-medium text-ink-gray-7 mb-1">{{ __('DocType') }}</label>
					<Combobox
						:modelValue="selectedDoctype"
						:query="doctypeQuery"
						:options="doctypeOptions"
						:placeholder="__('Select DocType…')"
						@update:query="(q) => (doctypeQuery = q)"
						@update:modelValue="onDoctypeSelect"
					/>
				</div>
				<div>
					<label class="block text-sm font-medium text-ink-gray-7 mb-1">{{ __('Path') }}</label>
					<input
						v-model="step.autocomplete_nav_path"
						type="text"
						class="w-full rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-outline-blue-3"
						placeholder="/app/sales-invoice/new-sales-invoice-1"
						@input="emit('dirty')"
					/>
				</div>
			</div>

			<div>
				<div class="flex items-center justify-between mb-2">
					<label class="block text-sm font-medium text-ink-gray-7">{{ __('URL Parameters') }}</label>
					<Button size="sm" variant="ghost" @click="addNavParam">
						<template #prefix><Plus class="w-3 h-3" /></template>
						{{ __('Add param') }}
					</Button>
				</div>
				<PlaceholderChips :tokens="NAV_TOKENS" class="mb-2" @insert="insertNavParamValue" />
				<div v-if="navParamRows.length" class="space-y-2">
					<div v-for="(row, i) in navParamRows" :key="i" class="flex gap-2 items-center">
						<input
							v-model="row.key"
							type="text"
							class="flex-1 rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-2 py-1.5 text-sm font-mono"
							:placeholder="__('Key')"
							@input="syncNavParams"
						/>
						<input
							v-model="row.value"
							type="text"
							class="flex-[2] rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-2 py-1.5 text-sm font-mono"
							:placeholder="__('Value or {placeholder}')"
							@input="syncNavParams"
						/>
						<Button variant="ghost" size="sm" @click="removeNavParam(i)">
							<X class="w-3.5 h-3.5" />
						</Button>
					</div>
				</div>
				<p v-else class="text-xs text-ink-gray-5 italic">{{ __('No URL parameters') }}</p>
				<details class="mt-2">
					<summary class="text-xs text-ink-gray-5 cursor-pointer">{{ __('Advanced: edit JSON') }}</summary>
					<textarea
						v-model="step.autocomplete_nav_params"
						rows="2"
						class="mt-1 w-full rounded border border-outline-gray-2 bg-surface-base text-ink-gray-8 px-2 py-1.5 text-xs font-mono"
						@input="onNavJsonInput"
					/>
				</details>
			</div>
		</div>
	</div>
</template>

<script setup>
import { Button, Combobox, FormControl } from 'frappe-ui'
import { computed, nextTick, ref, watch } from 'vue'
import { Info, Plus, X } from 'lucide-vue-next'
import PlaceholderChips from '@/components/Lab/PlaceholderChips.vue'
import { STEP_TOKENS, NAV_TOKENS, resolveLabPlaceholders, companyPrefixedChip } from '@/utils/labTokens'
import { STEP_FMT_BUTTONS, applyMarkdownFormat, renderStepInstructions } from '@/utils/labMarkdown'
import {
	doctypeToNavPath,
	parseNavParamsJson,
	serializeNavParamsJson,
	defaultNavParamsForDoctype,
} from '@/utils/labNav'

const props = defineProps({
	step: { type: Object, required: true },
	stepIdx: { type: Number, default: 0 },
	externalDoctypes: { type: Array, default: () => [] },
})

const emit = defineEmits(['dirty'])

const instructionsRef = ref(null)
const doctypeQuery = ref('')
const navParamRows = ref([])
const syncingNav = ref(false)

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

const selectedDoctype = computed(() => {
	const path = props.step?.autocomplete_nav_path || ''
	const m = path.match(/^\/app\/([^/]+)\//)
	if (!m) return ''
	const slug = m[1]
	return (props.externalDoctypes || []).find(
		(dt) => dt.toLowerCase().replace(/\s+/g, '-') === slug
	) || ''
})

const previewHtml = computed(() =>
	renderStepInstructions(props.step?.instructions, {
		stepIdx: props.stepIdx,
		resolve: resolveLabPlaceholders,
	})
)

function loadNavParams() {
	syncingNav.value = true
	navParamRows.value = parseNavParamsJson(props.step?.autocomplete_nav_params || '')
	syncingNav.value = false
}

watch(() => props.step?.autocomplete_nav_params, loadNavParams, { immediate: true })

function syncNavParams() {
	if (syncingNav.value) return
	props.step.autocomplete_nav_params = serializeNavParamsJson(navParamRows.value)
	emit('dirty')
}

function onNavJsonInput() {
	syncingNav.value = true
	navParamRows.value = parseNavParamsJson(props.step.autocomplete_nav_params || '')
	syncingNav.value = false
	emit('dirty')
}

function onDoctypeSelect(doctype) {
	if (!doctype || !props.step) return
	props.step.autocomplete_nav_path = doctypeToNavPath(doctype)
	navParamRows.value = defaultNavParamsForDoctype(doctype)
	syncNavParams()
	doctypeQuery.value = ''
	emit('dirty')
}

function addNavParam() {
	navParamRows.value.push({ key: '', value: '' })
}

function removeNavParam(i) {
	navParamRows.value.splice(i, 1)
	syncNavParams()
}

function insertNavParamValue(token) {
	const empty = navParamRows.value.find((r) => !r.value?.trim())
	if (empty) empty.value = token
	else navParamRows.value.push({ key: '', value: token })
	syncNavParams()
}

function applyFormat(cmd) {
	const ta = instructionsRef.value
	if (!ta) return
	applyMarkdownFormat(ta, props.step.instructions, cmd, (result, cursor) => {
		props.step.instructions = result
		emit('dirty')
		nextTick(() => {
			ta.focus()
			ta.setSelectionRange(cursor, cursor)
		})
	})
}

function insertToken(token) {
	const ta = instructionsRef.value
	if (!ta) return
	const start = ta.selectionStart ?? ta.value.length
	const end = ta.selectionEnd ?? ta.value.length
	props.step.instructions =
		props.step.instructions.substring(0, start) + token + props.step.instructions.substring(end)
	emit('dirty')
	nextTick(() => {
		ta.focus()
		ta.setSelectionRange(start + token.length, start + token.length)
	})
}

function insertPrefixedCodeChip() {
	const ta = instructionsRef.value
	const sel = ta
		? props.step.instructions.substring(ta.selectionStart ?? 0, ta.selectionEnd ?? 0).trim()
		: ''
	const suffix = window.prompt(
		__('Fixed code suffix after {company_name}- (e.g. KOSZULKA-LOGO-M-001):'),
		sel || 'KOSZULKA-LOGO-M-001',
	)
	if (!suffix?.trim()) return
	insertToken(companyPrefixedChip(__('Item code'), suffix.trim()))
}
</script>
