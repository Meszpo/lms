<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-surface-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="breadcrumbs" />
		<div class="flex items-center gap-x-2">
			<Badge v-if="isDirty" theme="orange">{{ __('Not Saved') }}</Badge>
			<Button variant="solid" @click="save" :loading="saving">{{ __('Save') }}</Button>
		</div>
	</header>

	<div v-if="lab" class="py-5">
		<!-- Details -->
		<div class="px-10 pb-6 space-y-5 border-b mb-6">
			<div class="text-lg font-semibold text-ink-gray-9">{{ __('Details') }}</div>
			<div class="grid grid-cols-2 gap-5">
				<FormControl
					v-model="lab.title"
					:label="__('Title')"
					:required="true"
					@input="isDirty = true"
				/>
				<Link
					v-model="lab.lab_connection"
					:label="__('Lab Connection')"
					doctype="LMS Lab Connection"
					@update:modelValue="isDirty = true"
				/>
				<FormControl
					v-model="lab.passing_percentage"
					:label="__('Passing Percentage')"
					type="number"
					@input="isDirty = true"
				/>
				<FormControl
					v-model="lab.max_attempts"
					:label="__('Max Attempts')"
					type="number"
					:description="__('0 = unlimited')"
					@input="isDirty = true"
				/>
				<FormControl
					v-model="lab.max_session_minutes"
					:label="__('Session Duration (minutes)')"
					type="number"
					@input="isDirty = true"
				/>
				<FormControl
					v-model="lab.company_prefix"
					:label="__('Company Prefix')"
					:description="__('Prefix used for generated company names')"
					@input="isDirty = true"
				/>
			</div>
		</div>

		<!-- Lab Description -->
		<div class="px-10 pb-6 border-b mb-6">
			<div class="text-lg font-semibold text-ink-gray-9 mb-1">{{ __('Lab Description') }}</div>
			<p class="text-xs text-ink-gray-5 mb-3">{{ __('Displayed on the course page. Supports Markdown formatting.') }}</p>
			<div class="grid grid-cols-2 gap-4">
				<!-- Editor -->
				<div class="border rounded-lg overflow-hidden flex flex-col">
					<div class="flex items-center gap-1 border-b bg-surface-gray-1 px-2 py-1.5 shrink-0">
						<span class="text-xs font-medium text-ink-gray-5 mr-1">{{ __('Markdown') }}</span>
						<button
							v-for="fmt in descFmtButtons"
							:key="fmt.cmd"
							type="button"
							:title="fmt.title"
							class="px-2 py-0.5 text-xs rounded hover:bg-surface-gray-3 text-ink-gray-7 font-medium transition-colors border border-transparent hover:border-outline-gray-2"
							@mousedown.prevent="applyDescFormat(fmt.cmd)"
						>{{ fmt.label }}</button>
					</div>
					<textarea
						ref="descTextareaRef"
						v-model="descMarkdown"
						rows="10"
						class="flex-1 px-3 py-2 text-sm font-mono text-ink-gray-8 focus:outline-none resize-none leading-relaxed"
						:placeholder="__('# Heading\n\nWrite lab description in **Markdown**…')"
						@input="isDirty = true"
					></textarea>
				</div>
				<!-- Preview -->
				<div class="border rounded-lg overflow-hidden flex flex-col">
					<div class="flex items-center border-b bg-surface-gray-1 px-2 py-1.5 shrink-0">
						<span class="text-xs font-medium text-ink-gray-5">{{ __('Preview') }}</span>
					</div>
					<div
						class="flex-1 px-4 py-3 text-sm text-ink-gray-8 leading-relaxed overflow-auto lab-desc-preview"
						v-html="renderedDesc || `<span class='text-ink-gray-4 text-xs italic'>${__('Nothing to preview yet…')}</span>`"
					></div>
				</div>
			</div>
		</div>

		<!-- User Roles -->
		<div class="px-10 pb-6 border-b mb-6">
			<div class="flex items-center justify-between mb-3">
				<div>
					<div class="text-lg font-semibold text-ink-gray-9">{{ __('User Roles') }}</div>
					<p class="text-xs text-ink-gray-5 mt-0.5">{{ __('Roles assigned to the student on the external system. Defaults to System Manager.') }}</p>
				</div>
				<Button size="sm" @click="addRole">
					<template #prefix><Plus class="w-3.5 h-3.5" /></template>
					{{ __('Add Role') }}
				</Button>
			</div>
			<div v-if="lab.roles?.length" class="space-y-2">
				<div v-for="(r, idx) in lab.roles" :key="idx" class="flex items-center gap-2">
					<input
						:value="r.role"
						type="text"
						class="flex-1 rounded border border-outline-gray-2 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-outline-blue-3"
						:placeholder="__('e.g. Sales User, Accounts User')"
						@input="setRoleValue(idx, $event.target.value)"
					/>
					<Button variant="ghost" size="sm" @click="removeRole(idx)">
						<X class="w-3.5 h-3.5 stroke-1.5 text-ink-gray-5" />
					</Button>
				</div>
			</div>
			<p v-else class="text-sm text-ink-gray-5 italic">{{ __('No roles configured — will use System Manager.') }}</p>
		</div>

		<!-- Steps -->
		<div class="px-10 pb-6 border-b mb-6">
			<div class="flex items-center justify-between mb-4">
				<div class="text-lg font-semibold text-ink-gray-9">
					{{ __('Steps') }}
					<span class="text-base font-normal text-ink-gray-5 ml-1">({{ lab.steps?.length || 0 }})</span>
				</div>
				<Button @click="openStepModal()">
					<template #prefix><Plus class="w-4 h-4" /></template>
					{{ __('Add Step') }}
				</Button>
			</div>
			<div v-if="lab.steps?.length" class="space-y-2">
				<div
					v-for="(step, idx) in lab.steps"
					:key="step.name || idx"
					class="flex items-start gap-3 p-3 border rounded-lg bg-surface-gray-1 hover:bg-surface-gray-2 cursor-pointer"
					@click="openStepModal(idx)"
				>
					<div class="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold"
						:class="(step.item_type || 'Step') === 'Text'
							? 'bg-surface-gray-3 text-ink-gray-5'
							: 'bg-surface-blue-1 text-ink-blue-3'"
					>
						{{ (step.item_type || 'Step') === 'Text' ? '¶' : (idx + 1) }}
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<span class="font-medium text-ink-gray-9 text-sm">{{ step.title || __('(untitled)') }}</span>
							<span v-if="(step.item_type || 'Step') === 'Text'"
								class="px-1.5 py-0.5 text-[10px] font-semibold uppercase rounded bg-surface-gray-2 text-ink-gray-5">
								{{ __('text') }}
							</span>
						</div>
						<div v-if="step.instructions" class="text-xs text-ink-gray-5 mt-0.5 truncate">
							{{ step.instructions.replace(/\+\[[^\]]+\]\([^)]+\)/g, '[chip]').replace(/<[^>]+>/g, '').substring(0, 80) }}
						</div>
					</div>
					<Button variant="ghost" size="sm" @click.stop="removeStep(idx)">
						<X class="w-3.5 h-3.5 stroke-1.5 text-ink-gray-5" />
					</Button>
				</div>
			</div>
			<p v-else class="text-sm text-ink-gray-5">{{ __('No steps added yet.') }}</p>
		</div>

		<!-- Evaluation Criteria -->
		<div class="px-10 pb-6">
			<div class="flex items-center justify-between mb-4">
				<div class="text-lg font-semibold text-ink-gray-9">
					{{ __('Evaluation Criteria') }}
					<span class="text-base font-normal text-ink-gray-5 ml-1">({{ lab.evaluation_criteria?.length || 0 }})</span>
				</div>
				<Button @click="openCriterionModal()">
					<template #prefix><Plus class="w-4 h-4" /></template>
					{{ __('Add Criterion') }}
				</Button>
			</div>
			<div v-if="lab.evaluation_criteria?.length" class="space-y-2">
				<div
					v-for="(criterion, idx) in lab.evaluation_criteria"
					:key="criterion.name || idx"
					class="flex items-start gap-3 p-3 border rounded-lg bg-surface-gray-1 hover:bg-surface-gray-2 cursor-pointer"
					@click="openCriterionModal(idx)"
				>
					<div class="flex-1 min-w-0">
						<div class="font-medium text-ink-gray-9 text-sm">{{ criterion.criterion_name || __('(unnamed)') }}</div>
						<div class="text-xs text-ink-gray-5 mt-0.5 flex gap-3">
							<span>{{ criterion.doctype_to_check }}</span>
							<span v-if="criterion.comparison_operator">{{ criterion.comparison_operator }}</span>
							<span v-if="criterion.expected_value" class="font-mono">{{ criterion.expected_value }}</span>
							<span class="font-medium text-ink-blue-3">{{ criterion.points }} pts</span>
						</div>
					</div>
					<Button variant="ghost" size="sm" @click.stop="removeCriterion(idx)">
						<X class="w-3.5 h-3.5 stroke-1.5 text-ink-gray-5" />
					</Button>
				</div>
			</div>
			<p v-else class="text-sm text-ink-gray-5">{{ __('No evaluation criteria added yet.') }}</p>
		</div>
	</div>

	<!-- Step Modal -->
	<Dialog
		v-model="showStepModal"
		:options="{
			title: editingStepIdx !== null ? __('Edit Step') : __('Add Step'),
			size: 'lg',
			actions: [
				{ label: __('Save'), variant: 'solid', onClick({ close }) { saveStep(close) } },
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					v-model="stepForm.item_type"
					:label="__('Item Type')"
					type="select"
					:options="[
						{ label: __('Step — numbered task with checkbox'), value: 'Step' },
						{ label: __('Text — free text / section header'), value: 'Text' },
					]"
					@change="isDirty = true"
				/>
				<FormControl v-model="stepForm.title" :label="__('Title')" :required="true" />

				<div>
					<div class="flex items-center justify-between mb-1">
						<label class="block text-sm font-medium text-ink-gray-7">{{ __('Instructions') }}</label>
					</div>
					<!-- Markdown toolbar -->
					<div class="mb-2 flex items-center gap-1 rounded-md bg-surface-gray-2 px-2 py-1.5 flex-wrap">
						<button
							v-for="fmt in mdFmtButtons"
							:key="fmt.cmd"
							type="button"
							:title="fmt.title"
							class="px-2 py-0.5 text-xs rounded hover:bg-surface-gray-4 text-ink-gray-7 font-medium transition-colors border border-transparent hover:border-outline-gray-2"
							@mousedown.prevent="applyMdFormat(fmt.cmd)"
						>{{ fmt.label }}</button>
						<span class="mx-1 text-outline-gray-3 text-xs select-none">|</span>
						<PlaceholderChips :tokens="stepTokens" @insert="insertAtCursor" />
					</div>
					<!-- Syntax hint -->
					<div class="mb-2 flex items-start gap-2 rounded-md bg-surface-gray-2 px-3 py-2 text-xs text-ink-gray-6">
						<Info class="size-3.5 shrink-0 mt-0.5 text-ink-gray-4" />
						<span>
							{{ __('Use') }}
							<code class="bg-surface-white rounded px-1 font-mono text-ink-blue-3">+[label](value)</code>
							{{ __('to embed a copyable chip.') }}
						</span>
					</div>
					<textarea
						ref="instructionsRef"
						v-model="stepForm.instructions"
						rows="7"
						class="w-full rounded border border-outline-gray-2 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-outline-blue-3"
						:placeholder="__('Describe what the student should do.\nUse +[Copy label](value) to add inline copyable values.')"
					/>
				</div>

				<div v-if="stepForm.item_type !== 'Text'" class="border-t pt-4">
					<div class="text-sm font-medium text-ink-gray-7 mb-3">
						{{ __('Navigation') }}
						<span class="font-normal text-ink-gray-4 text-xs ml-1">{{ __('(optional — opens a pre-filled form in the lab system window)') }}</span>
					</div>
					<div class="space-y-3">
						<div>
							<label class="block text-sm font-medium text-ink-gray-7 mb-1">{{ __('Path') }}</label>
							<input
								v-model="stepForm.autocomplete_nav_path"
								type="text"
								class="w-full rounded border border-outline-gray-2 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-outline-blue-3"
								placeholder="/app/sales-invoice/new-sales-invoice-1"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-ink-gray-7 mb-1">{{ __('Params (JSON)') }}</label>
							<PlaceholderChips :tokens="navTokens" @insert="insertAtCursor" class="mb-2" />
							<textarea
								v-model="stepForm.autocomplete_nav_params"
								rows="2"
								class="w-full rounded border border-outline-gray-2 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-outline-blue-3"
								:placeholder='`{\"company\": \"{company_name}\", \"customer\": \"ACME\"}`'
							/>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>

	<!-- Criterion Modal -->
	<Dialog
		v-model="showCriterionModal"
		:options="{
			title: editingCriterionIdx !== null ? __('Edit Criterion') : __('Add Criterion'),
			size: 'lg',
			actions: [
				{ label: __('Save'), variant: 'solid', onClick({ close }) { saveCriterion(close) } },
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					v-model="criterionForm.criterion_name"
					:label="__('Criterion Name')"
					:required="true"
				/>
				<div class="grid grid-cols-2 gap-3">
					<FormControl
						v-model="criterionForm.doctype_to_check"
						:label="__('DocType to Check')"
						:description="__('e.g. Sales Invoice')"
						:required="true"
					/>
					<FormControl
						v-model="criterionForm.points"
						:label="__('Points')"
						type="number"
					/>
					<FormControl
						v-model="criterionForm.comparison_operator"
						:label="__('Comparison')"
						type="select"
						:options="['Exists', 'Equals', 'Contains', 'Greater Than', 'Less Than']"
					/>
					<FormControl
						v-model="criterionForm.field_to_check"
						:label="__('Field to Check')"
						:description="__('Leave empty to check record existence only')"
					/>
					<FormControl
						v-model="criterionForm.expected_value"
						:label="__('Expected Value')"
						:description="__('Required for Equals/Contains/Greater/Less comparisons')"
						class="col-span-1"
					/>
				</div>
				<div>
					<div class="flex items-center justify-between mb-1">
						<label class="block text-sm font-medium text-ink-gray-7">
							{{ __('Filters (JSON array)') }}
						</label>
					</div>
					<!-- Placeholder chips for criterion -->
					<PlaceholderChips :tokens="criterionTokens" @insert="insertAtCursor" class="mb-2" />
					<textarea
						v-model="criterionForm.filters"
						rows="3"
						class="w-full rounded border border-outline-gray-2 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-outline-blue-3"
						:placeholder='`[[\"company\", \"=\", \"{company_name}\"]]`'
					/>
					<p class="text-xs text-ink-gray-5 mt-1">
						{{ __('Standard Frappe filter format. Placeholders above are replaced at evaluation time.') }}
					</p>
				</div>
				<FormControl
					v-model="criterionForm.description"
					:label="__('Description')"
					type="textarea"
					:rows="2"
				/>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Breadcrumbs,
	Button,
	Badge,
	Dialog,
	FormControl,
	createDocumentResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { computed, defineComponent, h, inject, onMounted, onBeforeUnmount, reactive, ref, nextTick, watch } from 'vue'
import { Plus, X, Info } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

// ── Markdown renderer (shared with LabWindow) ──────────────────────────────
function renderMarkdown(text) {
	if (!text) return ''
	const lines = text.split('\n')
	const out = []
	let inUl = false, inOl = false
	function closeList() {
		if (inUl) { out.push('</ul>'); inUl = false }
		if (inOl) { out.push('</ol>'); inOl = false }
	}
	function inline(s) {
		return s
			.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
			.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
			.replace(/`([^`\n]+)`/g, '<code>$1</code>')
			.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
	}
	for (const line of lines) {
		const h1 = line.match(/^# (.+)$/), h2 = line.match(/^## (.+)$/), h3 = line.match(/^### (.+)$/)
		const ul = line.match(/^[*-] (.+)$/), ol = line.match(/^\d+\. (.+)$/)
		const hr = line.match(/^---+$/)
		if (h1) { closeList(); out.push(`<h1>${inline(h1[1])}</h1>`) }
		else if (h2) { closeList(); out.push(`<h2>${inline(h2[1])}</h2>`) }
		else if (h3) { closeList(); out.push(`<h3>${inline(h3[1])}</h3>`) }
		else if (hr) { closeList(); out.push('<hr>') }
		else if (ul) {
			if (inOl) { out.push('</ol>'); inOl = false }
			if (!inUl) { out.push('<ul>'); inUl = true }
			out.push(`<li>${inline(ul[1])}</li>`)
		} else if (ol) {
			if (inUl) { out.push('</ul>'); inUl = false }
			if (!inOl) { out.push('<ol>'); inOl = true }
			out.push(`<li>${inline(ol[1])}</li>`)
		} else if (line.trim() === '') { closeList(); out.push('') }
		else { closeList(); out.push(`<p>${inline(line)}</p>`) }
	}
	closeList()
	return out.join('\n')
}

// ── Markdown toolbar for description ──────────────────────────────────────
const descTextareaRef = ref(null)
const descFmtButtons = [
	{ cmd: 'bold',   label: 'B',      title: 'Bold (**text**)' },
	{ cmd: 'italic', label: 'I',      title: 'Italic (*text*)' },
	{ cmd: 'code',   label: '</>',    title: 'Inline code' },
	{ cmd: 'h2',     label: 'H2',     title: 'Heading 2 (## text)' },
	{ cmd: 'h3',     label: 'H3',     title: 'Heading 3 (### text)' },
	{ cmd: 'ul',     label: '• List', title: 'Unordered list' },
	{ cmd: 'ol',     label: '1. List', title: 'Ordered list' },
]

function applyDescFormat(cmd) {
	const ta = descTextareaRef.value
	if (!ta) return
	const start = ta.selectionStart, end = ta.selectionEnd
	const sel = descMarkdown.value.substring(start, end)
	let insert = '', cursorOffset = 0
	if (cmd === 'bold')   { insert = `**${sel || 'bold text'}**`; cursorOffset = sel ? insert.length : 2 }
	else if (cmd === 'italic') { insert = `*${sel || 'italic text'}*`; cursorOffset = sel ? insert.length : 1 }
	else if (cmd === 'code')   { insert = `\`${sel || 'code'}\``; cursorOffset = sel ? insert.length : 1 }
	else if (cmd === 'h2') { insert = `## ${sel || 'Heading'}`; cursorOffset = insert.length }
	else if (cmd === 'h3') { insert = `### ${sel || 'Heading'}`; cursorOffset = insert.length }
	else if (cmd === 'ul') {
		insert = (sel || 'item').split('\n').map(l => `- ${l}`).join('\n'); cursorOffset = insert.length
	} else if (cmd === 'ol') {
		insert = (sel || 'item').split('\n').map((l, i) => `${i + 1}. ${l}`).join('\n'); cursorOffset = insert.length
	}
	descMarkdown.value = descMarkdown.value.substring(0, start) + insert + descMarkdown.value.substring(end)
	isDirty.value = true
	nextTick(() => {
		ta.focus()
		ta.setSelectionRange(start + cursorOffset, start + cursorOffset)
	})
}

// ── Markdown formatting buttons for step instructions ──────────────────────
const mdFmtButtons = [
	{ cmd: 'bold',    label: 'B',       title: 'Bold (**text**)' },
	{ cmd: 'italic',  label: 'I',       title: 'Italic (*text*)' },
	{ cmd: 'code',    label: '</>',     title: 'Inline code (`code`)' },
	{ cmd: 'ul',      label: '• Lista', title: 'Unordered list (- item)' },
	{ cmd: 'ol',      label: '1. Lista',title: 'Ordered list (1. item)' },
	{ cmd: 'check',   label: '☐ Checkbox', title: 'Checkbox item (- [ ] item) — student can tick off' },
]

function applyMdFormat(cmd) {
	const ta = instructionsRef.value
	if (!ta) return
	const start = ta.selectionStart
	const end = ta.selectionEnd
	const sel = ta.value.substring(start, end)
	let before = ta.value.substring(0, start)
	let after = ta.value.substring(end)
	let insert = '', cursorOffset = 0

	if (cmd === 'bold')   { insert = `**${sel || 'bold text'}**`; cursorOffset = sel ? insert.length : 2 }
	else if (cmd === 'italic') { insert = `*${sel || 'italic text'}*`; cursorOffset = sel ? insert.length : 1 }
	else if (cmd === 'code')   { insert = `\`${sel || 'code'}\``; cursorOffset = sel ? insert.length : 1 }
	else if (cmd === 'ul') {
		const lines = (sel || 'item').split('\n').map(l => `- ${l}`).join('\n')
		insert = lines; cursorOffset = insert.length
	} else if (cmd === 'ol') {
		const lines = (sel || 'item').split('\n').map((l, i) => `${i + 1}. ${l}`).join('\n')
		insert = lines; cursorOffset = insert.length
	} else if (cmd === 'check') {
		const lines = (sel || 'krok do wykonania').split('\n').map(l => `- [ ] ${l}`).join('\n')
		insert = lines; cursorOffset = insert.length
	}

	ta.value = before + insert + after
	ta.dispatchEvent(new Event('input', { bubbles: true }))
	nextTick(() => {
		const pos = start + cursorOffset
		ta.setSelectionRange(pos, pos)
		ta.focus()
	})
}
import { sessionStore } from '@/stores/session'
import Link from '@/components/Controls/Link.vue'

// Inline PlaceholderChips component
const PlaceholderChips = defineComponent({
	props: {
		tokens: { type: Array, required: true },
	},
	emits: ['insert'],
	setup(props, { emit }) {
		return () =>
			h('div', { class: 'flex flex-wrap gap-1.5 items-center' }, [
				h('span', { class: 'text-xs text-ink-gray-4' }, __('Variables:')),
				...props.tokens.map((t) =>
					h(
						'button',
						{
							type: 'button',
							title: t.description,
							class:
								'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono bg-surface-gray-2 hover:bg-surface-blue-1 text-ink-gray-7 hover:text-ink-blue-3 border border-outline-gray-2 hover:border-outline-blue-2 transition-colors cursor-pointer',
							onClick: () => emit('insert', t.value),
						},
						[
							h('span', {}, t.value),
						]
					)
				),
			])
	},
})

const { brand } = sessionStore()
const user = inject('$user')
const router = useRouter()
const isDirty = ref(false)
const saving = ref(false)
const showStepModal = ref(false)
const showCriterionModal = ref(false)
const editingStepIdx = ref(null)
const editingCriterionIdx = ref(null)
const instructionsRef = ref(null)

const props = defineProps({
	labID: { type: String, required: true },
})

// Available placeholder tokens per context
// Session-level (always available)
const SESSION_TOKENS = [
	{ value: '{username}',    description: __("Student's login on the external system") },
	{ value: '{password}',    description: __("Student's password on the external system") },
	{ value: '{company_name}',description: __('Generated company name for this student') },
	{ value: '{url}',         description: __('Base URL of the external system') },
]
// Randomized business data (generated per lab session by _generate_session_data)
const SESSION_DATA_TOKENS = [
	{ value: '{customer_name}',  description: __('Random Polish company name (customer)') },
	{ value: '{customer_type}',  description: __('Customer type: Company or Individual') },
	{ value: '{customer_group}', description: __('Customer group, e.g. Commercial') },
	{ value: '{territory}',      description: __('Sales territory, e.g. Poland') },
	{ value: '{tax_id}',         description: __('NIP / VAT number') },
	{ value: '{contact_first}',  description: __('Contact person — first name') },
	{ value: '{contact_last}',   description: __('Contact person — last name') },
	{ value: '{contact_full}',   description: __('Contact person — full name') },
	{ value: '{contact_email}',  description: __('Contact person — e-mail') },
	{ value: '{contact_phone}',  description: __('Contact person — phone') },
	{ value: '{addr_street}',    description: __('Address — street line') },
	{ value: '{addr_city}',      description: __('Address — city') },
	{ value: '{addr_pincode}',   description: __('Address — postal code') },
	{ value: '{item_name}',      description: __('Random product name') },
	{ value: '{item_code}',      description: __('Product code (item_name + token)') },
	{ value: '{item_group}',     description: __('Product group, e.g. Products') },
	{ value: '{item_uom}',       description: __('Unit of measure, e.g. Nos') },
	{ value: '{item_price}',     description: __('Selling price (PLN)') },
	{ value: '{order_qty}',      description: __('Order quantity') },
	{ value: '{discount_pct}',   description: __('Discount percentage') },
]

const stepTokens = [
	...SESSION_TOKENS,
	...SESSION_DATA_TOKENS,
]

const navTokens = [
	{ value: '{company_name}', description: __('Generated company name') },
	{ value: '{username}',     description: __("Student's login") },
	...SESSION_DATA_TOKENS,
]

const criterionTokens = [
	{ value: '{company_name}', description: __('Generated company name for this student') },
	{ value: '{username}',     description: __("Student's login on the external system") },
	...SESSION_DATA_TOKENS,
]

// Insert token at cursor in active input/textarea inside the dialog
function insertAtCursor(token) {
	const el = document.activeElement
	const inDialog = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') && el.closest('[role="dialog"]')
	if (inDialog) {
		const start = el.selectionStart ?? el.value.length
		const end = el.selectionEnd ?? el.value.length
		el.value = el.value.substring(0, start) + token + el.value.substring(end)
		el.dispatchEvent(new Event('input', { bubbles: true }))
		nextTick(() => {
			el.setSelectionRange(start + token.length, start + token.length)
			el.focus()
		})
	} else {
		// Fallback: focus the instructions textarea and append
		const ta = instructionsRef.value
		if (ta) {
			ta.focus()
			const pos = ta.selectionStart ?? ta.value.length
			const v = ta.value
			ta.value = v.substring(0, pos) + token + v.substring(pos)
			ta.dispatchEvent(new Event('input', { bubbles: true }))
			nextTick(() => ta.setSelectionRange(pos + token.length, pos + token.length))
		} else {
			navigator.clipboard.writeText(token).then(() => {
				toast({ title: __('Copied {0} — paste into the field', [token]), icon: 'check' })
			})
		}
	}
}

const stepForm = reactive({
	item_type: 'Step',
	title: '',
	instructions: '',
	autocomplete_nav_path: '',
	autocomplete_nav_params: '',
})

const criterionForm = reactive({
	criterion_name: '',
	doctype_to_check: '',
	filters: '',
	field_to_check: '',
	expected_value: '',
	comparison_operator: 'Exists',
	points: 10,
	description: '',
})

onMounted(() => {
	if (!user.data?.is_moderator && !user.data?.is_instructor) {
		router.push({ name: 'Courses' })
	}
	labDoc.reload()
	window.addEventListener('keydown', keyboardShortcut)
})

onBeforeUnmount(() => {
	window.removeEventListener('keydown', keyboardShortcut)
})

const keyboardShortcut = (e) => {
	if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
		save()
		e.preventDefault()
	}
}

const labDoc = createDocumentResource({
	doctype: 'LMS Lab',
	name: props.labID,
	auto: false,
	onError(err) {
		const msg = err?.messages?.[0] || ''
		if (msg.includes('DoesNotExist') || msg.includes('not found') || err?.exc_type === 'DoesNotExistError') {
			toast.error(__('Lab not found — it may have been deleted.'))
			router.push({ name: 'Labs' })
		}
	},
})

const lab = computed(() => labDoc.doc)

// Description markdown state — synced from/to lab.description
const descMarkdown = ref('')
const renderedDesc = computed(() => renderMarkdown(descMarkdown.value))

// Load description into textarea once lab doc arrives
watch(lab, (val) => {
	if (val && descMarkdown.value === '') {
		descMarkdown.value = val.description || ''
	}
}, { immediate: true })

// Keep lab.description in sync as user types
watch(descMarkdown, (val) => {
	if (lab.value) lab.value.description = val
})

const save = () => {
	if (!lab.value?.title) {
		toast.warning(__('Title is required'))
		return
	}
	saving.value = true
	labDoc.setValue.submit(
		{ ...lab.value },
		{
			onSuccess() {
				isDirty.value = false
				saving.value = false
				toast.success(__('Lab saved'))
			},
			onError(err) {
				saving.value = false
				toast.error(err?.messages?.[0] || __('Error saving lab'))
			},
		}
	)
}

// Step helpers
const openStepModal = (idx = null) => {
	editingStepIdx.value = idx
	if (idx !== null) {
		const s = lab.value.steps[idx]
		Object.assign(stepForm, {
			item_type: s.item_type || 'Step',
			title: s.title || '',
			instructions: s.instructions || '',
			autocomplete_nav_path: s.autocomplete_nav_path || '',
			autocomplete_nav_params: s.autocomplete_nav_params || '',
		})
	} else {
		Object.assign(stepForm, {
			item_type: 'Step', title: '', instructions: '',
			autocomplete_nav_path: '', autocomplete_nav_params: '',
		})
	}
	showStepModal.value = true
}

const saveStep = (close) => {
	if (!stepForm.title.trim()) {
		toast.warning(__('Step title is required'))
		return
	}
	const row = { ...stepForm, doctype: 'LMS Lab Step' }
	if (editingStepIdx.value !== null) {
		const existing = lab.value.steps[editingStepIdx.value]
		lab.value.steps[editingStepIdx.value] = { ...existing, ...row }
	} else {
		if (!lab.value.steps) lab.value.steps = []
		lab.value.steps.push(row)
	}
	isDirty.value = true
	close()
}

const removeStep = (idx) => {
	lab.value.steps.splice(idx, 1)
	isDirty.value = true
}

// Criterion helpers
const openCriterionModal = (idx = null) => {
	editingCriterionIdx.value = idx
	if (idx !== null) {
		const c = lab.value.evaluation_criteria[idx]
		Object.assign(criterionForm, {
			criterion_name: c.criterion_name || '',
			doctype_to_check: c.doctype_to_check || '',
			filters: c.filters || '',
			field_to_check: c.field_to_check || '',
			expected_value: c.expected_value || '',
			comparison_operator: c.comparison_operator || 'Exists',
			points: c.points ?? 10,
			description: c.description || '',
		})
	} else {
		Object.assign(criterionForm, {
			criterion_name: '', doctype_to_check: '', filters: '',
			field_to_check: '', expected_value: '', comparison_operator: 'Exists',
			points: 10, description: '',
		})
	}
	showCriterionModal.value = true
}

const saveCriterion = (close) => {
	if (!criterionForm.criterion_name.trim() || !criterionForm.doctype_to_check.trim()) {
		toast.warning(__('Criterion name and DocType are required'))
		return
	}
	const row = { ...criterionForm, doctype: 'LMS Lab Evaluation Criterion' }
	if (editingCriterionIdx.value !== null) {
		const existing = lab.value.evaluation_criteria[editingCriterionIdx.value]
		lab.value.evaluation_criteria[editingCriterionIdx.value] = { ...existing, ...row }
	} else {
		if (!lab.value.evaluation_criteria) lab.value.evaluation_criteria = []
		lab.value.evaluation_criteria.push(row)
	}
	isDirty.value = true
	close()
}

const removeCriterion = (idx) => {
	lab.value.evaluation_criteria.splice(idx, 1)
	isDirty.value = true
}

// Role helpers
const addRole = () => {
	const existing = lab.value.roles ? [...lab.value.roles] : []
	existing.push({ role: '', doctype: 'LMS Lab Role' })
	lab.value.roles = existing
	isDirty.value = true
}

const setRoleValue = (idx, value) => {
	const updated = [...(lab.value.roles || [])]
	updated[idx] = { ...updated[idx], role: value }
	lab.value.roles = updated
	isDirty.value = true
}

const removeRole = (idx) => {
	const updated = [...(lab.value.roles || [])]
	updated.splice(idx, 1)
	lab.value.roles = updated
	isDirty.value = true
}

const breadcrumbs = computed(() => [
	{ label: __('Labs'), route: { name: 'Labs' } },
	{ label: lab.value?.title || props.labID, route: { name: 'LabForm', params: { labID: props.labID } } },
])

usePageMeta(() => ({ title: lab.value?.title || __('Lab'), icon: brand.favicon }))
</script>

<style>
.lab-desc-preview h1 { font-size: 1.25rem; font-weight: 700; color: #111827; margin: 0.75rem 0 0.4rem; }
.lab-desc-preview h2 { font-size: 1.05rem; font-weight: 600; color: #1f2937; margin: 0.6rem 0 0.3rem; }
.lab-desc-preview h3 { font-size: 0.9rem;  font-weight: 600; color: #374151; margin: 0.5rem 0 0.2rem; }
.lab-desc-preview p  { margin: 0 0 0.4rem; line-height: 1.6; }
.lab-desc-preview ul { list-style-type: disc;    padding-left: 1.25rem; margin: 0.25rem 0; }
.lab-desc-preview ol { list-style-type: decimal; padding-left: 1.25rem; margin: 0.25rem 0; }
.lab-desc-preview li { margin: 0.1rem 0; line-height: 1.5; }
.lab-desc-preview hr { border: none; border-top: 1px solid #e5e7eb; margin: 0.75rem 0; }
.lab-desc-preview code {
	background: #f3f4f6; border: 1px solid #e5e7eb;
	border-radius: 3px; padding: 0.1rem 0.3rem;
	font-size: 0.82em; font-family: ui-monospace, monospace; color: #dc2626;
}
.lab-desc-preview a { color: #2563eb; text-decoration: underline; }
.lab-desc-preview strong { font-weight: 600; }
.lab-desc-preview em { font-style: italic; }
</style>
