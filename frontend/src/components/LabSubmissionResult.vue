<template>
	<div class="border rounded-lg overflow-hidden mb-4">
		<div
			class="flex items-center justify-between px-4 py-3"
			:class="submission.status === 'Pass' ? 'bg-green-50 border-b border-green-200' : 'bg-red-50 border-b border-red-200'"
		>
			<div class="flex items-center gap-2">
				<CheckCircle2 v-if="submission.status === 'Pass'" class="size-4 text-green-600" />
				<XCircle v-else class="size-4 text-red-500" />
				<span class="font-semibold text-sm" :class="submission.status === 'Pass' ? 'text-green-800' : 'text-red-800'">
					{{ submission.status === 'Pass' ? __('Lab Passed') : __('Lab Failed') }}
				</span>
			</div>
			<div class="text-sm text-ink-gray-5">
				{{ submission.score }} / {{ submission.max_score }} pts
				({{ Number(submission.percentage).toFixed(1) }}%)
			</div>
		</div>

		<div v-if="submission.results?.length" class="divide-y">
			<div
				v-for="r in submission.results"
				:key="r.criterion_name"
				class="flex items-start gap-3 px-4 py-2.5"
			>
				<CheckCircle2 v-if="r.passed" class="size-4 text-green-500 shrink-0 mt-0.5" />
				<XCircle v-else class="size-4 text-red-400 shrink-0 mt-0.5" />
				<div class="flex-1 min-w-0">
					<p class="text-sm font-medium text-ink-gray-8">{{ r.criterion_name }}</p>
					<p v-if="r.details" class="text-xs text-ink-gray-5 mt-0.5">{{ r.details }}</p>
				</div>
				<span class="text-xs font-semibold shrink-0" :class="r.passed ? 'text-green-700' : 'text-red-500'">
					{{ r.points_earned }} / {{ r.max_points }}
				</span>
			</div>
		</div>
	</div>
</template>

<script setup>
import { CheckCircle2, XCircle } from 'lucide-vue-next'

defineProps({
	submission: {
		type: Object,
		required: true,
	},
})
</script>
