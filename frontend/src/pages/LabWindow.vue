<template>
	<div class="h-screen flex flex-col bg-white">
		<!-- Header -->
		<header class="flex items-center justify-between border-b bg-white px-4 py-2.5 shrink-0 shadow-sm">
			<div class="flex items-center gap-2 min-w-0">
				<FlaskConical class="size-4 text-blue-600 shrink-0" />
				<span class="font-semibold text-gray-900 text-sm truncate">{{ labTitle }}</span>
			</div>
			<div class="flex items-center gap-2 shrink-0">
				<div v-if="instance" class="flex items-center gap-1.5 text-xs">
					<Timer class="size-3.5" :class="timeClass" />
					<span :class="timeClass" class="font-mono font-semibold">{{ formattedTime }}</span>
				</div>
				<button
					v-if="instance"
					class="px-2.5 py-1 text-xs font-medium text-red-600 border border-red-200 rounded hover:bg-red-50 transition-colors"
					:disabled="evaluating"
					@click="endLab"
				>{{ evaluating ? __('Closing…') : __('End Lab') }}</button>
			</div>
		</header>

		<!-- Loading state -->
		<div v-if="loading" class="flex-1 flex items-center justify-center">
			<div class="text-center">
				<LoaderCircle class="size-7 animate-spin mx-auto text-blue-500 mb-3" />
				<p class="text-sm text-gray-600">{{ __('Setting up your lab environment…') }}</p>
				<p class="text-xs text-gray-400 mt-1">{{ __('This may take up to 30 seconds.') }}</p>
			</div>
		</div>

		<!-- Error state (provision failed) -->
		<div v-else-if="error" class="flex-1 flex items-center justify-center p-6">
			<div class="text-center">
				<AlertCircle class="size-7 mx-auto text-red-400 mb-2" />
				<p class="font-medium text-gray-800 mb-1">{{ __('Failed to start lab') }}</p>
				<p class="text-sm text-gray-500 mb-4">{{ error }}</p>
				<button
					class="px-4 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
					@click="startProvision"
				>{{ __('Retry') }}</button>
			</div>
		</div>

		<!-- Evaluation error state -->
		<div v-else-if="evalError" class="flex-1 flex items-center justify-center p-6">
			<div class="text-center max-w-sm">
				<AlertCircle class="size-7 mx-auto text-orange-400 mb-2" />
				<p class="font-medium text-gray-800 mb-1">{{ __('Evaluation failed') }}</p>
				<p class="text-sm text-gray-500 mb-4">{{ evalError }}</p>
				<button
					class="px-4 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
					@click="retryEvaluate"
				>{{ __('Try again') }}</button>
			</div>
		</div>

		<!-- Results state -->
		<div v-else-if="evaluationResult" class="flex-1 overflow-auto p-5">
			<div class="text-center mb-5">
				<div
					class="inline-flex items-center justify-center w-14 h-14 rounded-full mb-3"
					:class="evaluationResult.status === 'Pass' ? 'bg-green-100' : 'bg-red-100'"
				>
					<CheckCircle2 v-if="evaluationResult.status === 'Pass'" class="size-7 text-green-600" />
					<XCircle v-else class="size-7 text-red-500" />
				</div>
				<h2 class="text-xl font-bold text-gray-900">
					{{ evaluationResult.status === 'Pass' ? __('Lab Passed!') : __('Lab Failed') }}
				</h2>
				<p class="text-sm text-gray-500 mt-1">
					{{ evaluationResult.score }} / {{ evaluationResult.max_score }} pkt
					({{ evaluationResult.percentage.toFixed(1) }}%)
				</p>
				<p class="text-xs text-gray-400 mt-0.5">
					{{ __('Required: ') }}{{ evaluationResult.passing_percentage }}%
				</p>
			</div>
			<div class="space-y-2">
				<div
					v-for="r in evaluationResult.results"
					:key="r.criterion_name"
					class="flex items-start gap-2.5 p-2.5 rounded-lg border text-sm"
					:class="r.passed ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'"
				>
					<CheckCircle2 v-if="r.passed" class="size-3.5 text-green-600 shrink-0 mt-0.5" />
					<XCircle v-else class="size-3.5 text-red-500 shrink-0 mt-0.5" />
					<div class="flex-1 min-w-0">
						<p class="font-medium text-gray-800">{{ r.criterion_name }}</p>
						<p class="text-xs text-gray-500 mt-0.5">{{ r.details }}</p>
					</div>
					<span class="text-xs font-semibold shrink-0" :class="r.passed ? 'text-green-700' : 'text-red-600'">
						{{ r.points_earned }}/{{ r.max_points }}
					</span>
				</div>
			</div>
			<button
				class="mt-5 w-full py-2 text-sm text-gray-600 border rounded hover:bg-gray-50"
				@click="closeWindow"
			>{{ __('Close') }}</button>
		</div>

		<!-- Active lab -->
		<template v-else-if="instance">
			<!-- Tab bar -->
			<div class="flex border-b bg-gray-50 shrink-0">
				<button
					v-for="tab in tabs"
					:key="tab"
					class="px-4 py-2 text-xs font-medium border-b-2 -mb-px transition-colors"
					:class="activeTab === tab
						? 'border-blue-500 text-blue-600 bg-white'
						: 'border-transparent text-gray-500 hover:text-gray-700'"
					@click="activeTab = tab"
				>{{ __(tab) }}</button>
			</div>

			<!-- Instructions tab -->
			<template v-if="activeTab === 'Instructions'">
				<!-- Open system banner -->
				<div class="border-b px-3 py-2 bg-blue-50 shrink-0">
					<!-- Row 1: URL + open button -->
					<div class="flex items-center justify-between gap-2 mb-1.5">
						<p class="text-xs text-blue-700 font-medium truncate min-w-0">{{ instance.url }}</p>
						<button
							class="shrink-0 flex items-center gap-1 px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded shadow-sm transition-colors"
							@click="openLabSystem"
						>
							<ExternalLink class="size-3" />
							{{ systemOpened ? __('Reopen system') : __('Open lab system') }}
						</button>
					</div>
					<!-- Row 2: credentials -->
					<div class="grid grid-cols-2 gap-x-3 gap-y-0.5">
						<!-- User -->
						<div class="flex items-center gap-1 min-w-0">
							<span class="text-xs text-gray-500 shrink-0">{{ __('User') }}:</span>
							<code class="text-xs font-mono truncate min-w-0 flex-1">{{ instance.external_username }}</code>
							<button
								class="cred-copy-btn shrink-0"
								:class="{ 'cred-copy-btn--copied': copiedKey === 'username' }"
								@click="copy(instance.external_username, 'username')"
								:title="copiedKey === 'username' ? __('Copied!') : __('Copy username')"
							>
								<Copy v-if="copiedKey !== 'username'" class="size-3" />
								<Check v-else class="size-3 cred-check-anim" />
								<span v-if="copiedKey === 'username'" class="cred-copied-label">{{ __('Copied') }}</span>
							</button>
						</div>
						<!-- Password -->
						<div class="flex items-center gap-1 min-w-0">
							<span class="text-xs text-gray-500 shrink-0">{{ __('Pass') }}:</span>
							<code class="text-xs font-mono truncate min-w-0 flex-1">{{ showPassword ? instance.external_password : '••••••' }}</code>
							<button class="text-blue-500 hover:text-blue-700 shrink-0" @click="showPassword = !showPassword">
								<Eye v-if="!showPassword" class="size-3" />
								<EyeOff v-else class="size-3" />
							</button>
							<button
								class="cred-copy-btn shrink-0"
								:class="{ 'cred-copy-btn--copied': copiedKey === 'password' }"
								@click="copy(instance.external_password, 'password')"
								:title="copiedKey === 'password' ? __('Copied!') : __('Copy password')"
							>
								<Copy v-if="copiedKey !== 'password'" class="size-3" />
								<Check v-else class="size-3 cred-check-anim" />
								<span v-if="copiedKey === 'password'" class="cred-copied-label">{{ __('Copied') }}</span>
							</button>
						</div>
					</div>
				</div>

				<!-- Progress bar (counts only Step items, not Text blocks) -->
				<div class="px-4 py-2 border-b shrink-0">
					<div class="flex justify-between items-center text-xs text-gray-500 mb-1">
						<span>{{ __('Progress') }}</span>
						<span class="font-medium">{{ checkedStepCount }} / {{ stepItemCount }} {{ __('done') }}</span>
					</div>
					<div class="h-1 bg-gray-200 rounded-full overflow-hidden">
						<div
							class="h-full bg-blue-500 rounded-full transition-all duration-300"
							:style="{ width: `${stepItemCount > 0 ? (checkedStepCount / stepItemCount) * 100 : 0}%` }"
						></div>
					</div>
				</div>

				<!-- Continuous scroll instructions (Skillable-style flowing list) -->
				<div class="flex-1 overflow-y-auto">
					<div class="px-5 py-4">
						<template v-for="(step, idx) in instance.steps" :key="step.idx">

							<!-- Text block: callout / section note -->
							<template v-if="(step.item_type || 'Step') === 'Text'">
								<div class="mb-4 rounded-md bg-amber-50 border-l-4 border-amber-400 px-4 py-3">
									<p v-if="step.title" class="font-semibold text-sm text-amber-900 mb-1">{{ step.title }}</p>
									<div
										class="instructions-body text-sm text-amber-800 leading-relaxed"
										v-html="renderedStep(step)"
										@click="handleBodyClick"
									></div>
								</div>
							</template>

							<!-- Step: task-list item with inline checkbox -->
							<template v-else>
								<div
									:id="`step-${idx}`"
									class="task-list-item mb-1"
									:class="checkedSteps.has(step.idx) ? 'opacity-60' : ''"
								>
									<label class="flex items-start gap-2.5 cursor-pointer select-none group">
										<input
											type="checkbox"
											:checked="checkedSteps.has(step.idx)"
											class="mt-1 shrink-0 rounded border-gray-400"
											style="accent-color: #3b82f6; width: 15px; height: 15px"
											@change="toggleCheck(step.idx)"
										/>
										<p
											class="font-semibold text-sm leading-snug"
											:class="checkedSteps.has(step.idx) ? 'line-through text-gray-400' : 'text-gray-900'"
										>{{ step.title }}</p>
									</label>
									<div class="ml-6 mt-1" v-if="step.instructions || step.autocomplete_nav_path">
										<div
											v-if="step.instructions"
											class="instructions-body text-gray-600 text-sm leading-relaxed"
											v-html="renderedStep(step)"
											@click="handleBodyClick"
										></div>
										<button
											v-if="step.autocomplete_nav_path"
											class="mt-2 flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 hover:underline"
											@click="openNavPath(step)"
										>
											<ExternalLink class="size-3" />
											{{ __('Open pre-filled form') }}
										</button>
									</div>
								</div>
								<!-- Hairline separator between steps -->
								<hr v-if="idx < instance.steps.length - 1 && (instance.steps[idx + 1]?.item_type || 'Step') === 'Step'" class="my-2 border-gray-100" />
							</template>

						</template>
					</div>

					<!-- Complete lab button at bottom of scroll -->
					<div class="px-5 py-5 border-t bg-gray-50">
						<button
							class="w-full flex items-center justify-center gap-2 py-2.5 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors"
							:disabled="evaluating"
							@click="endLab"
						>
							<CheckCircle2 class="size-4" />
							{{ evaluating ? __('Evaluating…') : __('Complete Lab') }}
						</button>
					</div>
				</div>
			</template>

			<!-- Resources tab -->
			<div v-else-if="activeTab === 'Resources'" class="flex-1 flex items-center justify-center p-8">
				<p class="text-sm text-gray-400 text-center">{{ __('No additional resources for this lab.') }}</p>
			</div>

			<!-- Help tab -->
			<div v-else class="flex-1 flex items-center justify-center p-8">
				<p class="text-sm text-gray-400 text-center">{{ __('Contact your instructor for assistance.') }}</p>
			</div>
		</template>
	</div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { call, toast } from 'frappe-ui'
import {
	FlaskConical,
	Timer,
	LoaderCircle,
	AlertCircle,
	CheckCircle2,
	XCircle,
	Copy,
	Check,
	Eye,
	EyeOff,
	ExternalLink,
} from 'lucide-vue-next'

const props = defineProps({
	labId: { type: String, required: true },
	lessonId: { type: String, required: true },
})

const loading = ref(false)
const error = ref(null)
const evalError = ref(null)
const instance = ref(null)
const evaluating = ref(false)
const evaluationResult = ref(null)
const showPassword = ref(false)
const labTitle = ref('')
const course = ref(null)
const activeTab = ref('Instructions')
const tabs = ['Instructions', 'Resources', 'Help']
const systemOpened = ref(false)
let labSystemWindow = null

// Countdown timer
const remainingSeconds = ref(0)
let timerInterval = null

const formattedTime = computed(() => {
	const s = remainingSeconds.value
	const m = Math.floor(s / 60)
	const sec = s % 60
	return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
})

const timeClass = computed(() => {
	if (remainingSeconds.value <= 300) return 'text-red-500'
	if (remainingSeconds.value <= 600) return 'text-orange-400'
	return 'text-gray-500'
})

// Personal step tracking
const storageKey = computed(() => `lms_lab_steps_${props.labId}_${props.lessonId}`)
const boxesKey   = computed(() => `lms_lab_boxes_${props.labId}_${props.lessonId}`)
const checkedSteps = ref(new Set())
const checkedBoxes = ref({}) // { "stepIdx:boxIdx": true }

// Only actual "Step" items count toward progress
const stepItemCount = computed(() =>
	(instance.value?.steps || []).filter(s => (s.item_type || 'Step') === 'Step').length
)
const checkedStepCount = computed(() => {
	const stepIdxSet = new Set(
		(instance.value?.steps || [])
			.filter(s => (s.item_type || 'Step') === 'Step')
			.map(s => s.idx)
	)
	return [...checkedSteps.value].filter(i => stepIdxSet.has(i)).length
})


function loadCheckedSteps() {
	try {
		const raw = localStorage.getItem(storageKey.value)
		if (raw) checkedSteps.value = new Set(JSON.parse(raw))
	} catch {
		checkedSteps.value = new Set()
	}
}

function loadCheckedBoxes() {
	try {
		const raw = localStorage.getItem(boxesKey.value)
		if (raw) checkedBoxes.value = JSON.parse(raw)
	} catch {
		checkedBoxes.value = {}
	}
}

function saveCheckedSteps() {
	localStorage.setItem(storageKey.value, JSON.stringify([...checkedSteps.value]))
}

function saveCheckedBoxes() {
	localStorage.setItem(boxesKey.value, JSON.stringify(checkedBoxes.value))
}

// Count `-[ ]` / `- [ ]` / `- [x]` items in a step's instructions text
function countTaskBoxes(text) {
	return (text?.match(/^- *\[[ x]?\] +.+/gim) || []).length
}

function toggleCheck(stepIdx) {
	const s = new Set(checkedSteps.value)
	const step = instance.value?.steps?.find(st => st.idx === stepIdx)
	const totalBoxes = countTaskBoxes(step?.instructions || '')
	const newBoxes = { ...checkedBoxes.value }

	if (s.has(stepIdx)) {
		s.delete(stepIdx)
		for (let i = 0; i < totalBoxes; i++) delete newBoxes[`${stepIdx}:${i}`]
	} else {
		s.add(stepIdx)
		for (let i = 0; i < totalBoxes; i++) newBoxes[`${stepIdx}:${i}`] = true
	}

	checkedBoxes.value = newBoxes
	checkedSteps.value = s
	saveCheckedBoxes()
	saveCheckedSteps()
}

function handleBoxClick(stepIdx, boxIdx) {
	const key = `${stepIdx}:${boxIdx}`
	const newBoxes = { ...checkedBoxes.value }
	if (newBoxes[key]) delete newBoxes[key]
	else newBoxes[key] = true
	checkedBoxes.value = newBoxes

	// Auto-check/uncheck the step when all its boxes match
	const step = instance.value?.steps?.find(st => st.idx === stepIdx)
	const total = countTaskBoxes(step?.instructions || '')
	if (total > 0) {
		const allDone = Array.from({ length: total }, (_, i) => newBoxes[`${stepIdx}:${i}`]).every(Boolean)
		const s = new Set(checkedSteps.value)
		if (allDone) s.add(stepIdx)
		else s.delete(stepIdx)
		checkedSteps.value = s
		saveCheckedSteps()
	}

	saveCheckedBoxes()
}

// Placeholder resolution
function resolvePlaceholders(text) {
	if (!text || !instance.value) return text || ''
	let out = text
		.replace(/{company_name}/g, instance.value.company_name || '')
		.replace(/{username}/g, instance.value.external_username || '')
		.replace(/{password}/g, instance.value.external_password || '')
		.replace(/{url}/g, instance.value.url || '')
	// Randomized per-session values (customer, item, address...) supplied by the backend.
	const sd = instance.value.session_data || {}
	for (const [key, value] of Object.entries(sd)) {
		out = out.replaceAll('{' + key + '}', value == null ? '' : String(value))
	}
	return out
}

// Basic markdown renderer with task-checkbox support (`- [ ] item` / `- [x] item`)
// ctx: { stepIdx, boxes } — boxes is checkedBoxes.value (reactive proxy access forces re-render)
function renderMarkdown(text, ctx = {}) {
	if (!text) return ''
	const { stepIdx, boxes } = ctx
	const lines = text.split('\n')
	const out = []
	let inUl = false, inOl = false, inTaskUl = false
	let boxCounter = 0

	function closeList() {
		if (inTaskUl) { out.push('</ul>'); inTaskUl = false }
		if (inUl)     { out.push('</ul>'); inUl = false }
		if (inOl)     { out.push('</ol>'); inOl = false }
	}

	function inlineMd(s) {
		return s
			.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
			.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
			.replace(/`([^`\n]+)`/g, '<code class="inline-code">$1</code>')
	}

	for (const line of lines) {
		// Checkbox item: `- [ ] text` or `- [x] text` or `-[] text`
		const cb = line.match(/^- *\[([x ]?)\] +(.+)$/i)
		const h3 = !cb && line.match(/^### (.+)$/)
		const h2 = !cb && line.match(/^## (.+)$/)
		const h1 = !cb && line.match(/^# (.+)$/)
		const ul = !cb && line.match(/^[*-] (.+)$/)
		const ol = !cb && line.match(/^\d+\. (.+)$/)

		if (cb) {
			const bi = boxCounter++
			const key = `${stepIdx}:${bi}`
			const checked = boxes?.[key] ?? (cb[1].toLowerCase() === 'x')
			if (inUl) { out.push('</ul>'); inUl = false }
			if (inOl) { out.push('</ol>'); inOl = false }
			if (!inTaskUl) { out.push('<ul class="task-list">'); inTaskUl = true }
			out.push(
				`<li class="task-item" data-task-item="1">` +
				`<input type="checkbox" class="task-check" data-step-idx="${stepIdx}" data-box-idx="${bi}"${checked ? ' checked' : ''} />` +
				`<span class="task-text">${inlineMd(cb[2])}</span>` +
				`</li>`
			)
		} else if (h3) { closeList(); out.push(`<h5 class="md-h5">${inlineMd(h3[1])}</h5>`) }
		else if (h2) { closeList(); out.push(`<h4 class="md-h4">${inlineMd(h2[1])}</h4>`) }
		else if (h1) { closeList(); out.push(`<h3 class="md-h3">${inlineMd(h1[1])}</h3>`) }
		else if (ul) {
			if (inOl)     { out.push('</ol>'); inOl = false }
			if (inTaskUl) { out.push('</ul>'); inTaskUl = false }
			if (!inUl)    { out.push('<ul class="md-ul">'); inUl = true }
			out.push(`<li>${inlineMd(ul[1])}</li>`)
		} else if (ol) {
			if (inUl)     { out.push('</ul>'); inUl = false }
			if (inTaskUl) { out.push('</ul>'); inTaskUl = false }
			if (!inOl)    { out.push('<ol class="md-ol">'); inOl = true }
			out.push(`<li>${inlineMd(ol[1])}</li>`)
		} else if (line.trim() === '') {
			closeList(); out.push('<div class="h-2"></div>')
		} else {
			closeList(); out.push(`<p class="md-p">${inlineMd(line)}</p>`)
		}
	}
	closeList()
	return out.join('')
}

const CHIP_RE = /\+\[([^\]]+)\]\(([^)]+)\)/g

const CLIPBOARD_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/></svg>`
const CHECK_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"/></svg>`

function renderedStep(step) {
	const text = step?.instructions
	if (!text) return ''
	const resolved = resolvePlaceholders(text)
	// Pass checkedBoxes.value so Vue tracks it as a dependency → re-renders on checkbox change
	const md = renderMarkdown(resolved, { stepIdx: step.idx, boxes: checkedBoxes.value })
	return md.replace(CHIP_RE, (_, label, value) => {
		const sv = value.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
		const sl = label.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
		return `<button class="lms-copy-chip" data-copy="${sv}" title="${sl}"><span class="lms-chip-icon">${CLIPBOARD_SVG}</span><span class="lms-chip-icon lms-chip-icon--check">${CHECK_SVG}</span><span class="lms-chip-label">${sv}</span><span class="lms-chip-copied">Copied to clipboard</span></button>`
	})
}

async function handleBodyClick(event) {
	// Task checkbox — prevent native toggle; manage state ourselves
	const taskItem = event.target.closest('[data-task-item]')
	if (taskItem) {
		event.preventDefault()
		const box = taskItem.querySelector('input.task-check')
		if (box) handleBoxClick(parseInt(box.dataset.stepIdx), parseInt(box.dataset.boxIdx))
		return
	}

	// Copy chip
	const chip = event.target.closest('.lms-copy-chip')
	if (!chip || chip.dataset.copied) return
	const value = chip.dataset.copy
	try {
		await navigator.clipboard.writeText(value)
		chip.dataset.copied = '1'
		setTimeout(() => delete chip.dataset.copied, 1600)
	} catch {
		toast({ title: value, icon: 'info' })
	}
}

// Open lab system in a new window positioned to the left of this panel
function openLabSystem() {
	if (!instance.value) return
	const url = instance.value.url + '/login'
	const panelW = window.outerWidth
	const screenW = window.screen.availWidth
	const screenH = window.screen.availHeight
	const labW = Math.max(screenW - panelW - 8, 800)
	labSystemWindow = window.open(url, 'lms_lab_system',
		`width=${labW},height=${screenH},left=0,top=0,resizable=yes`)
	if (labSystemWindow) {
		systemOpened.value = true
	} else {
		toast({ title: __('Pop-up blocked — allow pop-ups for this site in your browser settings.'), icon: 'x' })
	}
}

function openNavPath(step) {
	if (!instance.value || !step.autocomplete_nav_path) return
	let params = {}
	try {
		params = JSON.parse(resolvePlaceholders(step.autocomplete_nav_params || '{}'))
	} catch {}
	const qs = new URLSearchParams(params).toString()
	const url = `${instance.value.url}${step.autocomplete_nav_path}${qs ? '?' + qs : ''}`
	if (labSystemWindow && !labSystemWindow.closed) {
		labSystemWindow.location.href = url
		labSystemWindow.focus()
	} else {
		window.open(url, 'lms_lab_system')
	}
}

const copiedKey = ref(null)

async function copy(text, key) {
	try {
		await navigator.clipboard.writeText(text)
		copiedKey.value = key
		setTimeout(() => { if (copiedKey.value === key) copiedKey.value = null }, 1600)
	} catch {
		toast({ title: __('Copy failed'), icon: 'x' })
	}
}

async function startProvision() {
	console.log('[Lab] startProvision() called')
	// Clear step progress from any previous session — new session starts fresh
	localStorage.removeItem(storageKey.value)
	localStorage.removeItem(boxesKey.value)
	checkedSteps.value = new Set()
	checkedBoxes.value = {}

	loading.value = true
	error.value = null
	try {
		const data = await call('lms.lms.api.provision_lab_instance', {
			lab: props.labId,
			course: course.value || '',
			lesson: props.lessonId,
		})
		console.log('[Lab] provision_lab_instance success — instance:', data.instance, 'expires_at:', data.expires_at)
		instance.value = data
		labTitle.value = data.lab_title || props.labId
		startCountdown(data.expires_at)
		// Redirect the pre-opened loading window to the actual system URL.
		// Store the reference so endLab can reuse it without calling window.open again.
		try {
			const labWin = window.open('', 'lms_lab_system')
			if (labWin && !labWin.closed) {
				labWin.location.href = data.url + '/login'
				labWin.focus()
				labSystemWindow = labWin
				systemOpened.value = true
			}
		} catch {}
	} catch (e) {
		error.value = e.message || String(e)
	} finally {
		loading.value = false
	}
}

function startCountdown(expiresAt) {
	if (timerInterval) clearInterval(timerInterval)
	const expiry = new Date(expiresAt).getTime()
	function tick() {
		const diff = Math.max(0, Math.floor((expiry - Date.now()) / 1000))
		remainingSeconds.value = diff
		if (diff === 0) { clearInterval(timerInterval); handleSessionExpired() }
	}
	tick()
	timerInterval = setInterval(tick, 1000)
}

async function handleSessionExpired() {
	toast({ title: __('Session expired. Evaluating and cleaning up…'), icon: 'alert-circle' })
	await endLab()
}


async function endLab() {
	if (evaluating.value) return
	evaluating.value = true
	if (timerInterval) clearInterval(timerInterval)

	// Close the external system window
	if (labSystemWindow && !labSystemWindow.closed) {
		try { labSystemWindow.close() } catch {}
	}
	labSystemWindow = null

	// Notify Lesson.vue that cleanup has started
	try {
		if (typeof BroadcastChannel !== 'undefined') {
			const ch = new BroadcastChannel('lms_lab_results')
			ch.postMessage({ type: 'lab_ended', lab: props.labId })
			ch.close()
		}
	} catch {}

	// Await enqueue so the HTTP request completes before the window closes.
	// The server returns immediately (just queues the job), so this is fast.
	try {
		await call('lms.lms.api.enqueue_evaluate_lab', {
			lab: props.labId,
			lesson: props.lessonId,
			course: course.value || '',
		})
	} catch {}

	window.close()
}

async function retryEvaluate() {
	evalError.value = null
	await endLab()
}

function closeWindow() {
	window.close()
}

onMounted(async () => {
	console.log('[Lab] onMounted — labId:', props.labId, 'lessonId:', props.lessonId)
	const params = new URLSearchParams(window.location.search)
	course.value = params.get('course') || ''
	loadCheckedSteps()
	loadCheckedBoxes()

	// Enforce max panel width — snap back if user drags wider than 400px
	const enforceWidth = () => {
		if (window.outerWidth > 400) {
			try { window.resizeTo(400, window.outerHeight) } catch {}
		}
	}
	window.addEventListener('resize', enforceWidth, { passive: true })

	console.log('[Lab] checking for existing instance…')
	const existing = await call('lms.lms.api.get_lab_instance', { lab: props.labId })
	console.log('[Lab] get_lab_instance result:', existing)
	if (existing) {
		instance.value = existing
		labTitle.value = existing.lab_title || props.labId
		startCountdown(existing.expires_at)
		try {
			const labWin = window.open('', 'lms_lab_system')
			if (labWin && !labWin.closed) {
				labWin.location.href = existing.url + '/login'
				labWin.focus()
				labSystemWindow = labWin
				systemOpened.value = true
			}
		} catch {}
	} else {
		console.log('[Lab] no existing instance — provisioning new…')
		await startProvision()
	}
})

onBeforeUnmount(() => {
	if (timerInterval) clearInterval(timerInterval)
})
</script>

<style>
/* Copy chip */
@keyframes lms-chip-copied {
	0%   { transform: scale(1); }
	20%  { transform: scale(1.06); }
	100% { transform: scale(1); }
}
@keyframes lms-chip-fade-in {
	from { opacity: 0; transform: translateY(2px); }
	to   { opacity: 1; transform: translateY(0); }
}

.instructions-body .lms-copy-chip {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 1px 7px 1px 5px;
	height: 20px;
	border-radius: 3px;
	font-size: 0.72rem;
	font-family: ui-monospace, 'Cascadia Code', monospace;
	font-weight: 600;
	background: #eff6ff;
	color: #1d4ed8;
	border: 1px solid #bfdbfe;
	cursor: pointer;
	vertical-align: middle;
	transition: background 0.2s, border-color 0.2s, color 0.2s;
	max-width: 300px;
	overflow: hidden;
	white-space: nowrap;
	position: relative;
}
.instructions-body .lms-copy-chip:hover {
	background: #dbeafe;
	border-color: #93c5fd;
}

/* Icon elements */
.instructions-body .lms-chip-icon {
	display: inline-flex;
	align-items: center;
	flex-shrink: 0;
	opacity: 0.7;
}
.instructions-body .lms-chip-icon--check { display: none; }

/* Label / copied text */
.instructions-body .lms-chip-label {
	overflow: hidden;
	text-overflow: ellipsis;
}
.instructions-body .lms-chip-copied {
	display: none;
	white-space: nowrap;
}

/* Copied state */
.instructions-body .lms-copy-chip[data-copied] {
	background: #dcfce7;
	border-color: #86efac;
	color: #15803d;
	animation: lms-chip-copied 0.3s ease-out;
}
.instructions-body .lms-copy-chip[data-copied] .lms-chip-icon:not(.lms-chip-icon--check) { display: none; }
.instructions-body .lms-copy-chip[data-copied] .lms-chip-icon--check {
	display: inline-flex;
	animation: lms-chip-fade-in 0.2s ease-out;
}
.instructions-body .lms-copy-chip[data-copied] .lms-chip-label { display: none; }
.instructions-body .lms-copy-chip[data-copied] .lms-chip-copied {
	display: inline;
	animation: lms-chip-fade-in 0.2s ease-out;
	font-family: ui-sans-serif, system-ui, sans-serif;
	font-weight: 500;
	font-size: 0.7rem;
}

/* Task checklist (- [ ] item) */
.instructions-body .task-list {
	list-style: none;
	padding: 0;
	margin: 0.3rem 0;
}
.instructions-body .task-item {
	display: flex;
	align-items: flex-start;
	gap: 0.45rem;
	padding: 0.15rem 0.25rem;
	border-radius: 4px;
	cursor: pointer;
	margin: 1px 0;
	transition: background 0.1s;
}
.instructions-body .task-item:hover { background: rgba(59, 130, 246, 0.06); }
.instructions-body .task-item:has(input:checked) .task-text {
	text-decoration: line-through;
	color: #9ca3af;
}
.instructions-body .task-check {
	margin-top: 2px;
	width: 13px;
	height: 13px;
	flex-shrink: 0;
	accent-color: #3b82f6;
	pointer-events: none; /* click handled by parent li via event delegation */
}
.instructions-body .task-text {
	font-size: inherit;
	line-height: 1.5;
}

/* Markdown styles */
.instructions-body .md-h3 { font-size: 1rem; font-weight: 700; color: #111827; margin: 0.75rem 0 0.25rem; }
.instructions-body .md-h4 { font-size: 0.875rem; font-weight: 600; color: #1f2937; margin: 0.5rem 0 0.2rem; }
.instructions-body .md-h5 { font-size: 0.8125rem; font-weight: 600; color: #374151; margin: 0.375rem 0 0.15rem; }
.instructions-body .md-ul { list-style-type: disc; padding-left: 1.1rem; margin: 0.25rem 0; }
.instructions-body .md-ol { list-style-type: decimal; padding-left: 1.1rem; margin: 0.25rem 0; }
.instructions-body .md-ul li, .instructions-body .md-ol li { margin: 0.1rem 0; }
.instructions-body .md-p { margin: 0 0 0.25rem; }
.instructions-body .inline-code {
	background: #f3f4f6;
	padding: 0.1rem 0.3rem;
	border-radius: 3px;
	font-size: 0.8em;
	font-family: ui-monospace, monospace;
	color: #dc2626;
	border: 1px solid #e5e7eb;
}

/* Credential copy buttons */
@keyframes cred-check-in {
	from { opacity: 0; transform: scale(0.5); }
	to   { opacity: 1; transform: scale(1); }
}
@keyframes cred-copied-in {
	from { opacity: 0; transform: translateX(-4px); }
	to   { opacity: 1; transform: translateX(0); }
}
.cred-copy-btn {
	display: inline-flex;
	align-items: center;
	gap: 3px;
	color: #3b82f6;
	transition: color 0.15s;
	border-radius: 4px;
	padding: 1px 3px;
}
.cred-copy-btn:hover { color: #1d4ed8; }
.cred-copy-btn--copied {
	color: #15803d;
}
.cred-check-anim {
	animation: cred-check-in 0.18s ease-out;
}
.cred-copied-label {
	font-size: 0.65rem;
	font-weight: 600;
	animation: cred-copied-in 0.18s ease-out;
}
</style>
