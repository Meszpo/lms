<template>
	<div class="space-y-6">
		<div v-if="previewData?.description || descHtml" class="rounded-lg border overflow-hidden">
			<div class="px-3 py-2 border-b bg-surface-gray-1 text-sm font-medium text-ink-gray-7">
				{{ __('Course page description') }}
			</div>
			<div class="px-4 py-3 text-sm lab-desc-preview" v-html="descHtml" />
		</div>

		<div class="rounded-lg border overflow-hidden">
			<div class="px-3 py-2 border-b bg-surface-blue-1 flex items-center justify-between">
				<span class="text-sm font-medium text-ink-blue-8">{{ __('Instructions (student view)') }}</span>
				<Badge theme="blue">{{ __('Preview') }}</Badge>
			</div>
			<div class="px-5 py-4 space-y-4 max-h-[60vh] overflow-y-auto">
				<template v-for="(step, idx) in steps" :key="idx">
					<div
						v-if="(step.item_type || 'Step') === 'Text'"
						class="rounded-md bg-surface-amber-1 border-l-4 border-outline-amber-3 px-4 py-3"
					>
						<p v-if="step.title" class="font-semibold text-sm text-ink-amber-9 mb-1">{{ step.title }}</p>
						<div class="text-sm text-ink-amber-8 lab-step-preview" v-html="renderStep(step, idx)" />
					</div>
					<div v-else class="flex gap-3">
						<div
							class="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm font-semibold"
							:class="checkedSteps.has(idx) ? 'bg-surface-green-2 text-ink-green-7' : 'bg-surface-blue-2 text-ink-blue-6'"
						>
							{{ stepNumber(idx) }}
						</div>
						<div class="flex-1 min-w-0">
							<div class="font-medium text-sm text-ink-gray-9">{{ step.title }}</div>
							<div class="text-sm text-ink-gray-7 mt-1 lab-step-preview" v-html="renderStep(step, idx)" />
							<p
								v-if="step.autocomplete_nav_path"
								class="text-xs text-ink-blue-6 mt-2 font-mono truncate"
							>
								→ {{ step.autocomplete_nav_path }}
							</p>
						</div>
					</div>
				</template>
				<p v-if="!steps.length" class="text-sm text-ink-gray-5 italic">{{ __('No steps to preview') }}</p>
			</div>
		</div>

		<div v-if="criteria.length" class="rounded-lg border overflow-hidden">
			<div class="px-3 py-2 border-b bg-surface-gray-1 text-sm font-medium text-ink-gray-7">
				{{ __('Evaluation criteria') }}
				<span class="text-ink-gray-5 font-normal ml-1">({{ totalPoints }} {{ __('pts') }})</span>
			</div>
			<div class="divide-y">
				<div v-for="(c, i) in criteria" :key="i" class="px-4 py-2.5 flex justify-between text-sm">
					<div>
						<div class="font-medium text-ink-gray-9">{{ c.criterion_name }}</div>
						<div class="text-xs text-ink-gray-5 mt-0.5">{{ c.doctype_to_check }} · {{ c.comparison_operator }}</div>
					</div>
					<span class="text-ink-blue-6 font-medium shrink-0">{{ c.points }} pts</span>
				</div>
			</div>
			<div class="px-4 py-2 bg-surface-gray-1 text-xs text-ink-gray-5 border-t">
				{{ __('Passing: {0}%').format(passingPercentage) }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { Badge } from 'frappe-ui'
import { computed, ref } from 'vue'
import { renderLabDescriptionMarkdown, renderStepInstructions } from '@/utils/labMarkdown'
import { resolveLabPlaceholders } from '@/utils/labTokens'

const props = defineProps({
	lab: { type: Object, default: null },
	previewData: { type: Object, default: null },
})

const checkedSteps = ref(new Set())

const steps = computed(() => props.previewData?.steps || props.lab?.steps || [])
const criteria = computed(() => props.previewData?.evaluation_criteria || props.lab?.evaluation_criteria || [])
const passingPercentage = computed(() =>
	props.previewData?.passing_percentage ?? props.lab?.passing_percentage ?? 70
)
const totalPoints = computed(() =>
	criteria.value.reduce((s, c) => s + (Number(c.points) || 0), 0)
)

const descHtml = computed(() => {
	const desc = props.lab?.description || ''
	return renderLabDescriptionMarkdown(desc)
})

function stepNumber(idx) {
	let n = 0
	for (let i = 0; i <= idx; i++) {
		if ((steps.value[i]?.item_type || 'Step') === 'Step') n++
	}
	return n
}

function renderStep(step, idx) {
	const sessionData = props.previewData?.session_data || {}
	const data = { ...sessionData }
	if (props.previewData) {
		data.username = props.previewData.external_username
		data.password = props.previewData.external_password
		data.company_name = props.previewData.company_name
		data.url = props.previewData.url
	}
	return renderStepInstructions(step.instructions, {
		stepIdx: idx,
		resolve: (text) => {
			let out = text
			for (const [key, value] of Object.entries(data)) {
				out = out.replaceAll(`{${key}}`, value == null ? '' : String(value))
			}
			return out
		},
	})
}
</script>
