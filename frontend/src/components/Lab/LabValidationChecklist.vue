<template>
	<ul class="space-y-1.5 text-xs">
		<li
			v-for="item in items"
			:key="item.id"
			class="flex items-start gap-2"
			:class="item.ok ? 'text-ink-gray-6' : item.warn ? 'text-ink-amber-6' : 'text-ink-red-6'"
		>
			<Check v-if="item.ok" class="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
			<AlertTriangle v-else-if="item.warn" class="w-3.5 h-3.5 shrink-0 mt-0.5" />
			<X v-else class="w-3.5 h-3.5 shrink-0 mt-0.5" />
			<span>{{ item.label }}</span>
		</li>
	</ul>
</template>

<script setup>
import { computed } from 'vue'
import { Check, X, AlertTriangle } from 'lucide-vue-next'
import { PLACEHOLDER_RE } from '@/utils/labTokens'

const props = defineProps({
	lab: { type: Object, default: null },
	connectionOk: { type: Boolean, default: null },
	totalCriteriaPoints: { type: Number, default: 0 },
})

const stepCount = computed(() =>
	(props.lab?.steps || []).filter((s) => (s.item_type || 'Step') === 'Step').length
)

const criteriaWithoutCompany = computed(() =>
	(props.lab?.evaluation_criteria || []).filter((c) => {
		const filters = (c.filters || '').toLowerCase()
		if (!c.doctype_to_check) return false
		if (filters.includes('company')) return false
		// Item has no company field — session-prefixed item_code isolates students
		if (c.doctype_to_check.toLowerCase() === 'item' && filters.includes('{company_name}')) return false
		return true
	}).length
)

const seedRecordsWithoutPlaceholder = computed(() =>
	(props.lab?.seed_records || []).filter((r) => {
		if (!r.label?.trim()) return false
		return !PLACEHOLDER_RE.test(r.field_values || '')
	}).length
)

const minPassPoints = computed(() => {
	const pct = Number(props.lab?.passing_percentage) || 0
	const total = props.totalCriteriaPoints || 0
	return Math.ceil((pct / 100) * total)
})

const items = computed(() => {
	const lab = props.lab
	if (!lab) return []

	const list = [
		{
			id: 'title',
			ok: !!lab.title?.trim(),
			label: lab.title?.trim() ? __('Title set') : __('Title is required'),
		},
		{
			id: 'connection',
			ok: !!lab.lab_connection,
			warn: lab.lab_connection && props.connectionOk === false,
			label: !lab.lab_connection
				? __('Lab Connection not selected')
				: props.connectionOk === false
					? __('Lab Connection unreachable — check settings')
					: props.connectionOk === true
						? __('Lab Connection verified')
						: __('Lab Connection selected'),
		},
		{
			id: 'steps',
			ok: stepCount.value > 0,
			label: stepCount.value > 0
				? __('{0} task step(s)').format(stepCount.value)
				: __('No task steps — add at least one Step'),
		},
		{
			id: 'criteria',
			ok: (lab.evaluation_criteria?.length || 0) > 0 && props.totalCriteriaPoints > 0,
			label: !(lab.evaluation_criteria?.length)
				? __('No evaluation criteria')
				: props.totalCriteriaPoints === 0
					? __('Total points is 0 — students cannot pass')
					: __('{0} criteria · {1} pts total').format(lab.evaluation_criteria.length, props.totalCriteriaPoints),
		},
		{
			id: 'passing',
			ok: props.totalCriteriaPoints > 0 && minPassPoints.value <= props.totalCriteriaPoints,
			warn: props.totalCriteriaPoints > 0 && minPassPoints.value > 0,
			label: props.totalCriteriaPoints === 0
				? __('Set passing percentage after adding criteria')
				: __('Passing: {0}% = min. {1}/{2} pts').format(
					lab.passing_percentage || 0,
					minPassPoints.value,
					props.totalCriteriaPoints,
				),
		},
	]

	if (criteriaWithoutCompany.value > 0) {
		list.push({
			id: 'company-filter',
			ok: false,
			warn: true,
			label: __('{0} criterion/criteria without company filter — students may match others\' data').format(
				criteriaWithoutCompany.value,
			),
		})
	}

	if (seedRecordsWithoutPlaceholder.value > 0) {
		list.push({
			id: 'seed-placeholder',
			ok: false,
			warn: true,
			label: __('{0} seed record(s) with no placeholder value — concurrent students would collide').format(
				seedRecordsWithoutPlaceholder.value,
			),
		})
	}

	return list
})

defineExpose({ allOk: computed(() => items.value.every((i) => i.ok || i.warn)) })
</script>
