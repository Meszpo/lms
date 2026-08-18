<template>
	<PageHeader :breadcrumbs="breadcrumbs">
		<template #actions>
			<Badge v-if="isDirty" theme="orange">{{ __('Not Saved') }}</Badge>
			<HeaderButton
				:label="__('Test Lab')"
				icon="lucide-flask-conical"
				:disabled="!lab?.title"
				@click="openTestLab"
			/>
			<Button variant="solid" @click="save" :loading="saving" :disabled="!isDirty">
				{{ __('Save') }}
			</Button>
		</template>
	</PageHeader>

	<div v-if="lab" class="grid flex-1 grid-cols-1 lg:min-h-0 lg:grid-cols-[1fr,320px]">
		<!-- Main column -->
		<div class="flex min-w-0 flex-col lg:min-h-0 lg:overflow-y-auto">
			<!-- Tab stepper -->
			<div class="flex border-b px-5 gap-1 shrink-0">
				<button
					v-for="tab in tabs"
					:key="tab.id"
					type="button"
					class="px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors"
					:class="activeTab === tab.id
						? 'border-outline-blue-3 text-ink-blue-6'
						: 'border-transparent text-ink-gray-5 hover:text-ink-gray-7'"
					@click="activeTab = tab.id"
				>
					{{ tab.label }}
					<span v-if="tab.count != null" class="text-ink-gray-4 font-normal ml-1">({{ tab.count }})</span>
				</button>
			</div>

			<div class="p-5 space-y-5">
				<!-- BASICS TAB -->
				<template v-if="activeTab === 'basics'">
					<div class="flex items-center justify-between">
						<h2 class="text-lg font-semibold text-ink-gray-9">{{ __('Lab Description') }}</h2>
						<Dropdown :options="templateOptions">
							<Button size="sm" variant="outline">
								<template #prefix><LayoutTemplate class="w-3.5 h-3.5" /></template>
								{{ __('Apply template') }}
							</Button>
						</Dropdown>
					</div>
					<p class="text-xs text-ink-gray-5 -mt-3">{{ __('Displayed on the course page. Supports Markdown formatting.') }}</p>
					<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
						<div class="border rounded-lg overflow-hidden flex flex-col bg-surface-base">
							<div class="flex items-center gap-1 border-b bg-surface-gray-1 px-2 py-1.5 shrink-0 flex-wrap">
								<span class="text-xs font-medium text-ink-gray-5 mr-1">{{ __('Markdown') }}</span>
								<button
									v-for="fmt in DESC_FMT_BUTTONS"
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
								rows="12"
								class="flex-1 px-3 py-2 text-sm font-mono text-ink-gray-8 bg-surface-base focus:outline-none resize-none leading-relaxed"
								:placeholder="__('# Heading\n\nWrite lab description in **Markdown**…')"
								@input="isDirty = true"
							></textarea>
						</div>
						<div class="border rounded-lg overflow-hidden flex flex-col bg-surface-base">
							<div class="flex items-center border-b bg-surface-gray-1 px-2 py-1.5 shrink-0">
								<span class="text-xs font-medium text-ink-gray-5">{{ __('Preview') }}</span>
							</div>
							<div
								class="flex-1 px-4 py-3 text-sm text-ink-gray-8 leading-relaxed overflow-auto lab-desc-preview bg-surface-base"
								v-html="renderedDesc || `<span class='text-ink-gray-4 text-xs italic'>${__('Nothing to preview yet…')}</span>`"
							></div>
						</div>
					</div>

					<!-- User Roles -->
					<div class="border-t pt-5">
						<div class="flex items-center justify-between mb-3">
							<div>
								<div class="text-lg font-semibold text-ink-gray-9">{{ __('User Roles') }}</div>
								<p class="text-xs text-ink-gray-5 mt-0.5">{{ __('Roles assigned to the student on the external system. Defaults to System Manager.') }}</p>
								<p v-if="lab.lab_connection && !externalRoles && !loadingExternalRoles" class="text-xs text-ink-amber-6 mt-0.5">
									{{ __('Could not verify roles against the external system — check the names manually.') }}
								</p>
							</div>
							<Button size="sm" @click="addRole">
								<template #prefix><Plus class="w-3.5 h-3.5" /></template>
								{{ __('Add Role') }}
							</Button>
						</div>
						<div v-if="lab.roles?.length" class="space-y-1">
							<div v-for="(r, idx) in lab.roles" :key="idx">
								<div class="flex items-center gap-2">
									<Combobox
										class="flex-1"
										:modelValue="r.role"
										:query="roleQueries[idx] || ''"
										:options="roleOptionsFor(idx)"
										:placeholder="__('e.g. Sales User, Accounts User')"
										@update:query="(q) => (roleQueries[idx] = q)"
										@update:modelValue="(val) => setRoleValue(idx, val || '')"
									/>
									<Check
										v-if="r.role?.trim() && externalRoles && !isDuplicateRole(idx) && !isUnknownRole(idx)"
										class="w-3.5 h-3.5 text-green-500 shrink-0"
									/>
									<Button variant="ghost" size="sm" @click="removeRole(idx)">
										<X class="w-3.5 h-3.5 stroke-1.5 text-ink-gray-5" />
									</Button>
								</div>
								<p v-if="isDuplicateRole(idx)" class="text-xs text-red-500 mt-0.5">
									{{ __('This role is assigned more than once.') }}
								</p>
								<p v-else-if="isUnknownRole(idx)" class="text-xs text-red-500 mt-0.5">
									{{ __('Role not found on the external system.') }}
								</p>
							</div>
						</div>
						<p v-else class="text-sm text-ink-gray-5 italic">{{ __('No roles configured — will use System Manager.') }}</p>
					</div>
				</template>

				<!-- STEPS TAB -->
				<template v-if="activeTab === 'steps'">
					<div class="flex items-center justify-between mb-2">
						<h2 class="text-lg font-semibold text-ink-gray-9">{{ __('Steps') }}</h2>
						<Button @click="addStep">
							<template #prefix><Plus class="w-4 h-4" /></template>
							{{ __('Add Step') }}
						</Button>
					</div>
					<Draggable
						v-if="lab.steps?.length"
						v-model="lab.steps"
						item-key="name"
						handle=".step-drag-handle"
						@end="onStepsReordered"
						class="space-y-2"
					>
						<template #item="{ element: step, index: idx }">
							<div class="border rounded-lg bg-surface-gray-1 overflow-hidden">
								<div
									class="flex items-start gap-2 p-3 cursor-pointer hover:bg-surface-gray-2"
									@click="toggleExpandedStep(idx)"
								>
									<GripVertical class="step-drag-handle w-4 h-4 text-ink-gray-4 shrink-0 mt-0.5 cursor-grab" />
									<div
										class="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold"
										:class="(step.item_type || 'Step') === 'Text'
											? 'bg-surface-gray-3 text-ink-gray-5'
											: 'bg-surface-blue-2 text-ink-blue-6'"
									>
										{{ (step.item_type || 'Step') === 'Text' ? '¶' : stepNumber(idx) }}
									</div>
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2">
											<span class="font-medium text-ink-gray-9 text-sm">{{ step.title || __('(untitled)') }}</span>
											<span v-if="(step.item_type || 'Step') === 'Text'"
												class="px-1.5 py-0.5 text-[10px] font-semibold uppercase rounded bg-surface-gray-2 text-ink-gray-5">
												{{ __('text') }}
											</span>
										</div>
										<div v-if="step.instructions && expandedStepIdx !== idx" class="text-xs text-ink-gray-5 mt-0.5 truncate">
											{{ stripInstructions(step.instructions) }}
										</div>
									</div>
									<div class="flex items-center gap-1 shrink-0">
										<Button variant="ghost" size="sm" :title="__('Duplicate')" @click.stop="duplicateStep(idx)">
											<Copy class="w-3.5 h-3.5 text-ink-gray-5" />
										</Button>
										<Button variant="ghost" size="sm" @click.stop="removeStep(idx)">
											<X class="w-3.5 h-3.5 stroke-1.5 text-ink-gray-5" />
										</Button>
										<ChevronDown
											class="w-4 h-4 text-ink-gray-4 transition-transform"
											:class="{ 'rotate-180': expandedStepIdx === idx }"
										/>
									</div>
								</div>
								<div v-if="expandedStepIdx === idx" class="px-4 pb-4">
									<LabStepEditor
										:step="step"
										:step-idx="idx"
										:external-doctypes="externalDoctypes"
										@dirty="isDirty = true"
									/>
								</div>
							</div>
						</template>
					</Draggable>
					<p v-else class="text-sm text-ink-gray-5">{{ __('No steps added yet.') }}</p>
				</template>

				<!-- EVALUATION TAB -->
				<template v-if="activeTab === 'evaluation'">
					<div class="flex items-center justify-between mb-2">
						<div>
							<h2 class="text-lg font-semibold text-ink-gray-9">{{ __('Evaluation Criteria') }}</h2>
							<p class="text-sm mt-0.5"
								:class="totalCriteriaPoints === 0 ? 'text-red-500' : 'text-ink-gray-5'"
							>
								{{ __('Total: {0} pts').format(totalCriteriaPoints) }}
								<span v-if="totalCriteriaPoints === 0">{{ __('— cannot pass with 0 points') }}</span>
							</p>
						</div>
						<Button @click="addCriterion">
							<template #prefix><Plus class="w-4 h-4" /></template>
							{{ __('Add Criterion') }}
						</Button>
					</div>
					<Draggable
						v-if="lab.evaluation_criteria?.length"
						v-model="lab.evaluation_criteria"
						item-key="name"
						handle=".criterion-drag-handle"
						@end="isDirty = true"
						class="space-y-2"
					>
						<template #item="{ element: criterion, index: idx }">
							<div class="border rounded-lg bg-surface-gray-1 overflow-hidden">
								<div
									class="flex items-start gap-2 p-3 cursor-pointer hover:bg-surface-gray-2"
									@click="toggleExpandedCriterion(idx)"
								>
									<GripVertical class="criterion-drag-handle w-4 h-4 text-ink-gray-4 shrink-0 mt-1 cursor-grab" />
									<div class="flex-1 min-w-0">
										<div class="font-medium text-ink-gray-9 text-sm">{{ criterion.criterion_name || __('(unnamed)') }}</div>
										<div class="text-xs text-ink-gray-5 mt-0.5 flex flex-wrap gap-2">
											<span>{{ criterion.doctype_to_check }}</span>
											<span v-if="criterion.comparison_operator">{{ criterion.comparison_operator }}</span>
											<span class="font-medium text-ink-blue-6">{{ criterion.points }} pts</span>
										</div>
									</div>
									<div class="flex items-center gap-1 shrink-0">
										<Button variant="ghost" size="sm" :title="__('Duplicate')" @click.stop="duplicateCriterion(idx)">
											<Copy class="w-3.5 h-3.5 text-ink-gray-5" />
										</Button>
										<Button variant="ghost" size="sm" @click.stop="removeCriterion(idx)">
											<X class="w-3.5 h-3.5 stroke-1.5 text-ink-gray-5" />
										</Button>
										<ChevronDown
											class="w-4 h-4 text-ink-gray-4 transition-transform"
											:class="{ 'rotate-180': expandedCriterionIdx === idx }"
										/>
									</div>
								</div>
								<div v-if="expandedCriterionIdx === idx" class="px-4 pb-4">
									<LabCriterionEditor
										:criterion="criterion"
										:lab-connection="lab.lab_connection"
										:external-doctypes="externalDoctypes"
										@dirty="isDirty = true"
									/>
								</div>
							</div>
						</template>
					</Draggable>
					<p v-else class="text-sm text-ink-gray-5">{{ __('No evaluation criteria added yet.') }}</p>
				</template>

				<!-- PREVIEW TAB -->
				<template v-if="activeTab === 'preview'">
					<div class="flex items-center justify-between mb-4">
						<h2 class="text-lg font-semibold text-ink-gray-9">{{ __('Preview') }}</h2>
						<Button variant="outline" size="sm" :loading="loadingPreview" @click="loadPreviewData">
							{{ __('Refresh preview data') }}
						</Button>
					</div>
					<LabPreviewPanel :lab="lab" :preview-data="previewData" />
				</template>
			</div>
		</div>

		<!-- Sidebar -->
		<div class="order-first border-b p-5 space-y-6 lg:order-none lg:overflow-y-auto lg:border-b-0 lg:border-s bg-surface-gray-1/50">
			<div class="space-y-4">
				<h2 class="text-base font-semibold text-ink-gray-9">{{ __('Details') }}</h2>
				<FormControl
					v-model="lab.title"
					:label="__('Title')"
					variant="outline"
					:required="true"
					@input="isDirty = true"
				/>
				<div>
					<Link
						v-model="lab.lab_connection"
						:label="__('Lab Connection')"
						doctype="LMS Lab Connection"
						@update:modelValue="onConnectionChange"
					/>
					<div v-if="lab.lab_connection" class="flex items-center gap-1.5 mt-1">
						<span
							class="w-2 h-2 rounded-full shrink-0"
							:class="{
								'bg-ink-gray-3': connectionStatus === null,
								'bg-green-500': connectionStatus === true,
								'bg-red-500': connectionStatus === false,
							}"
						/>
						<span class="text-xs text-ink-gray-5">
							{{ connectionStatus === true ? __('Connection OK') : connectionStatus === false ? __('Connection failed') : __('Checking…') }}
						</span>
					</div>
				</div>
				<FormControl
					v-model="lab.passing_percentage"
					:label="__('Passing Percentage')"
					type="number"
					variant="outline"
					@input="isDirty = true"
				/>
			</div>

			<details class="group">
				<summary class="text-sm font-semibold text-ink-gray-9 cursor-pointer list-none flex items-center justify-between">
					{{ __('Advanced settings') }}
					<ChevronDown class="w-4 h-4 text-ink-gray-4 group-open:rotate-180 transition-transform" />
				</summary>
				<div class="mt-4 space-y-4">
					<FormControl
						v-model="lab.max_attempts"
						:label="__('Max Attempts')"
						type="number"
						variant="outline"
						:description="__('0 = unlimited')"
						@input="isDirty = true"
					/>
					<FormControl
						v-model="lab.max_session_minutes"
						:label="__('Session Duration (minutes)')"
						type="number"
						variant="outline"
						@input="isDirty = true"
					/>
					<FormControl
						v-model="lab.company_prefix"
						:label="__('Company Prefix')"
						variant="outline"
						:description="__('Prefix used for generated company names')"
						@input="isDirty = true"
					/>
				</div>
			</details>

			<div class="border-t pt-4">
				<h3 class="text-sm font-semibold text-ink-gray-9 mb-2">{{ __('Checklist') }}</h3>
				<LabValidationChecklist
					:lab="lab"
					:connection-ok="connectionStatus"
					:total-criteria-points="totalCriteriaPoints"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import {
	Button,
	Badge,
	Combobox,
	Dropdown,
	FormControl,
	createDocumentResource,
	call,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject, onMounted, onBeforeUnmount, reactive, ref, nextTick, watch } from 'vue'
import {
	Plus, X, Check, Copy, GripVertical, ChevronDown, LayoutTemplate,
} from 'lucide-vue-next'
import Draggable from 'vuedraggable'
import { useRouter } from 'vue-router'
import { sessionStore } from '@/stores/session'
import Link from '@/components/Controls/Link.vue'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import LabStepEditor from '@/components/Lab/LabStepEditor.vue'
import LabCriterionEditor from '@/components/Lab/LabCriterionEditor.vue'
import LabPreviewPanel from '@/components/Lab/LabPreviewPanel.vue'
import LabValidationChecklist from '@/components/Lab/LabValidationChecklist.vue'
import { getLmsRoute } from '@/utils/basePath'
import { DESC_FMT_BUTTONS, renderLabDescriptionMarkdown } from '@/utils/labMarkdown'
import { LAB_TEMPLATES, applyLabTemplate } from '@/utils/labTemplates'

const { brand } = sessionStore()
const user = inject('$user')
const router = useRouter()
const isDirty = ref(false)
const saving = ref(false)
const activeTab = ref('basics')
const expandedStepIdx = ref(null)
const expandedCriterionIdx = ref(null)
const descTextareaRef = ref(null)
const connectionStatus = ref(null)
const loadingPreview = ref(false)
const previewData = ref(null)
const externalDoctypes = ref([])
const loadingExternalDoctypes = ref(false)

const props = defineProps({
	labID: { type: String, required: true },
})

const tabs = computed(() => [
	{ id: 'basics', label: __('Basics') },
	{ id: 'steps', label: __('Steps'), count: lab.value?.steps?.length || 0 },
	{ id: 'evaluation', label: __('Evaluation'), count: lab.value?.evaluation_criteria?.length || 0 },
	{ id: 'preview', label: __('Preview') },
])

const templateOptions = computed(() =>
	LAB_TEMPLATES.map((tpl) => ({
		label: tpl.label,
		onClick: () => applyTemplate(tpl.id),
	}))
)

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

const descMarkdown = ref('')
const renderedDesc = computed(() => renderLabDescriptionMarkdown(descMarkdown.value))

watch(lab, (val) => {
	if (val && descMarkdown.value === '') {
		descMarkdown.value = val.description || ''
	}
}, { immediate: true })

watch(descMarkdown, (val) => {
	if (lab.value) lab.value.description = val
})

watch(activeTab, (tab) => {
	if (tab === 'preview' && !previewData.value) loadPreviewData()
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

function applyTemplate(templateId) {
	if (!confirm(__('Apply this template? Existing steps and criteria will be replaced.'))) return
	if (applyLabTemplate(lab.value, templateId)) {
		isDirty.value = true
		activeTab.value = 'steps'
		toast.success(__('Template applied'))
	}
}

function applyDescFormat(cmd) {
	const ta = descTextareaRef.value
	if (!ta) return
	const start = ta.selectionStart
	const end = ta.selectionEnd
	const sel = descMarkdown.value.substring(start, end)
	let insert = ''
	let cursorOffset = 0
	if (cmd === 'bold') { insert = `**${sel || 'bold text'}**`; cursorOffset = sel ? insert.length : 2 }
	else if (cmd === 'italic') { insert = `*${sel || 'italic text'}*`; cursorOffset = sel ? insert.length : 1 }
	else if (cmd === 'code') { insert = `\`${sel || 'code'}\``; cursorOffset = sel ? insert.length : 1 }
	else if (cmd === 'h2') { insert = `## ${sel || 'Heading'}`; cursorOffset = insert.length }
	else if (cmd === 'h3') { insert = `### ${sel || 'Heading'}`; cursorOffset = insert.length }
	else if (cmd === 'ul') {
		insert = (sel || 'item').split('\n').map((l) => `- ${l}`).join('\n')
		cursorOffset = insert.length
	} else if (cmd === 'ol') {
		insert = (sel || 'item').split('\n').map((l, i) => `${i + 1}. ${l}`).join('\n')
		cursorOffset = insert.length
	}
	descMarkdown.value = descMarkdown.value.substring(0, start) + insert + descMarkdown.value.substring(end)
	isDirty.value = true
	nextTick(() => {
		ta.focus()
		ta.setSelectionRange(start + cursorOffset, start + cursorOffset)
	})
}

function stripInstructions(text) {
	return text.replace(/\+\[[^\]]+\]\([^)]+\)/g, '[chip]').replace(/<[^>]+>/g, '').substring(0, 80)
}

function stepNumber(idx) {
	let n = 0
	for (let i = 0; i <= idx; i++) {
		if ((lab.value?.steps?.[i]?.item_type || 'Step') === 'Step') n++
	}
	return n
}

// Steps
function addStep() {
	if (!lab.value.steps) lab.value.steps = []
	lab.value.steps.push({
		doctype: 'LMS Lab Step',
		item_type: 'Step',
		title: '',
		instructions: '',
		autocomplete_nav_path: '',
		autocomplete_nav_params: '',
	})
	expandedStepIdx.value = lab.value.steps.length - 1
	isDirty.value = true
}

function toggleExpandedStep(idx) {
	expandedStepIdx.value = expandedStepIdx.value === idx ? null : idx
}

function removeStep(idx) {
	lab.value.steps.splice(idx, 1)
	if (expandedStepIdx.value === idx) expandedStepIdx.value = null
	isDirty.value = true
}

function duplicateStep(idx) {
	const src = lab.value.steps[idx]
	const copy = { ...src, name: undefined, doctype: 'LMS Lab Step' }
	lab.value.steps.splice(idx + 1, 0, copy)
	expandedStepIdx.value = idx + 1
	isDirty.value = true
}

function onStepsReordered() {
	isDirty.value = true
}

// Criteria
function addCriterion() {
	if (!lab.value.evaluation_criteria) lab.value.evaluation_criteria = []
	lab.value.evaluation_criteria.push({
		doctype: 'LMS Lab Evaluation Criterion',
		criterion_name: '',
		doctype_to_check: '',
		filters: '',
		field_to_check: '',
		expected_value: '',
		comparison_operator: 'Exists',
		points: 10,
		description: '',
	})
	expandedCriterionIdx.value = lab.value.evaluation_criteria.length - 1
	isDirty.value = true
}

function toggleExpandedCriterion(idx) {
	expandedCriterionIdx.value = expandedCriterionIdx.value === idx ? null : idx
}

function removeCriterion(idx) {
	lab.value.evaluation_criteria.splice(idx, 1)
	if (expandedCriterionIdx.value === idx) expandedCriterionIdx.value = null
	isDirty.value = true
}

function duplicateCriterion(idx) {
	const src = lab.value.evaluation_criteria[idx]
	const copy = { ...src, name: undefined, doctype: 'LMS Lab Evaluation Criterion' }
	lab.value.evaluation_criteria.splice(idx + 1, 0, copy)
	expandedCriterionIdx.value = idx + 1
	isDirty.value = true
}

const totalCriteriaPoints = computed(() =>
	(lab.value?.evaluation_criteria || []).reduce((sum, c) => sum + (Number(c.points) || 0), 0)
)

// Connection & external data
async function testConnection(connection) {
	if (!connection) {
		connectionStatus.value = null
		return
	}
	connectionStatus.value = null
	try {
		const result = await call('lms.lms.api.test_lab_connection', { lab_connection: connection })
		connectionStatus.value = !!result?.ok
	} catch {
		connectionStatus.value = false
	}
}

async function loadExternalDoctypes(connection) {
	if (!connection) {
		externalDoctypes.value = []
		return
	}
	loadingExternalDoctypes.value = true
	try {
		externalDoctypes.value = await call('lms.lms.api.get_external_doctypes', { lab_connection: connection })
	} catch {
		externalDoctypes.value = []
	} finally {
		loadingExternalDoctypes.value = false
	}
}

function onConnectionChange() {
	isDirty.value = true
	loadExternalRoles()
	testConnection(lab.value?.lab_connection)
	loadExternalDoctypes(lab.value?.lab_connection)
}

// Roles
const externalRoles = ref(null)
const loadingExternalRoles = ref(false)
const roleQueries = reactive({})

const loadExternalRoles = async () => {
	const connection = lab.value?.lab_connection
	if (!connection) {
		externalRoles.value = null
		return
	}
	loadingExternalRoles.value = true
	try {
		externalRoles.value = await call('lms.lms.api.get_external_roles', { lab_connection: connection })
	} catch {
		externalRoles.value = null
	} finally {
		loadingExternalRoles.value = false
	}
}

watch(
	() => lab.value?.lab_connection,
	(val, oldVal) => {
		if (val && val !== oldVal) {
			loadExternalRoles()
			testConnection(val)
			loadExternalDoctypes(val)
		} else if (!val) {
			externalRoles.value = null
			connectionStatus.value = null
			externalDoctypes.value = []
		}
	}
)

const roleCounts = computed(() => {
	const counts = {}
	for (const r of lab.value?.roles || []) {
		const v = (r.role || '').trim()
		if (v) counts[v] = (counts[v] || 0) + 1
	}
	return counts
})

const isDuplicateRole = (idx) => {
	const v = (lab.value.roles[idx]?.role || '').trim()
	return !!v && roleCounts.value[v] > 1
}

const isUnknownRole = (idx) => {
	const v = (lab.value.roles[idx]?.role || '').trim()
	if (!v || !externalRoles.value) return false
	return !externalRoles.value.includes(v)
}

const roleOptionsFor = (idx) => {
	const options = (externalRoles.value || []).map((name) => ({ label: name, value: name }))
	const query = (roleQueries[idx] || '').trim()
	const current = (lab.value.roles[idx]?.role || '').trim()
	if (
		query &&
		query.toLowerCase() !== current.toLowerCase() &&
		!options.some((o) => o.value.toLowerCase() === query.toLowerCase())
	) {
		options.unshift({ label: __('Use "{0}"').format(query), value: query })
	}
	return options
}

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
	roleQueries[idx] = ''
	isDirty.value = true
}

const removeRole = (idx) => {
	const updated = [...(lab.value.roles || [])]
	updated.splice(idx, 1)
	lab.value.roles = updated
	for (let i = idx; i < updated.length; i++) {
		roleQueries[i] = roleQueries[i + 1] || ''
	}
	delete roleQueries[updated.length]
	isDirty.value = true
}

// Preview & test
async function loadPreviewData() {
	loadingPreview.value = true
	try {
		previewData.value = await call('lms.lms.api.get_lab_preview', { lab: props.labID })
	} catch (err) {
		toast.error(err?.messages?.[0] || __('Could not load preview'))
	} finally {
		loadingPreview.value = false
	}
}

function openTestLab() {
	const labPath = encodeURIComponent(props.labID)
	const url = getLmsRoute(`/labs/${labPath}/_preview?preview=1`)
	const panelW = 420
	const screenH = window.screen.availHeight
	const previewWin = window.open(
		url,
		'lms_lab_preview',
		`width=${panelW},height=${screenH},resizable=yes,scrollbars=yes`
	)
	if (!previewWin) {
		window.location.href = url
	}
}

const breadcrumbs = computed(() => [
	{ label: __('Labs'), route: { name: 'Labs' } },
	{ label: lab.value?.title || props.labID, route: { name: 'LabForm', params: { labID: props.labID } } },
])

usePageMeta(() => ({ title: lab.value?.title || __('Lab'), icon: brand.favicon }))
</script>
