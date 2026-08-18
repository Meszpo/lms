<template>
	<div class="space-y-2">
		<div v-for="group in visibleGroups" :key="group.id" class="flex flex-wrap gap-1.5 items-center">
			<span class="text-xs font-medium text-ink-gray-5 w-full">{{ group.label }}</span>
			<button
				v-for="t in group.tokens"
				:key="t.value"
				type="button"
				:title="tokenTitle(t)"
				class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono bg-surface-gray-2 hover:bg-surface-blue-2 text-ink-gray-7 hover:text-ink-blue-6 border border-outline-gray-2 hover:border-outline-blue-2 transition-colors cursor-pointer"
				@click="emit('insert', t.value)"
			>
				<span>{{ t.value }}</span>
				<span v-if="t.example" class="text-ink-gray-4 font-sans normal-case">→ {{ t.example }}</span>
			</button>
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { TOKEN_GROUPS } from '@/utils/labTokens'

const props = defineProps({
	tokens: { type: Array, required: true },
	grouped: { type: Boolean, default: true },
})

const emit = defineEmits(['insert'])

const tokenTitle = (t) => {
	const parts = [t.description]
	if (t.example) parts.push(__('Example: {0}').format(t.example))
	return parts.join(' — ')
}

const visibleGroups = computed(() => {
	if (!props.grouped) {
		return [{ id: 'all', label: __('Variables'), tokens: props.tokens }]
	}
	const byGroup = {}
	for (const t of props.tokens) {
		const gid = t.group || 'session'
		if (!byGroup[gid]) byGroup[gid] = []
		byGroup[gid].push(t)
	}
	return TOKEN_GROUPS.filter((g) => byGroup[g.id]?.length).map((g) => ({
		...g,
		tokens: byGroup[g.id],
	}))
})
</script>
