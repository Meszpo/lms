<template>
	<SettingsLayout
		v-if="view === 'list'"
		:title="label"
		:description="__(description || '')"
	>
		<template #header-actions>
			<Button variant="solid" @click="openForm('new')">
				<template #prefix>
					<Plus class="h-4 w-4 stroke-1.5" />
				</template>
				{{ __('New') }}
			</Button>
		</template>
		<div v-if="labConnections.data?.length">
			<ListView
				:columns="columns"
				:rows="labConnections.data"
				row-key="name"
				:options="{
					showTooltip: false,
					onRowClick: (row) => openForm(row.name),
				}"
			>
				<ListHeader
					class="mb-2 grid items-center gap-x-4 rounded bg-surface-gray-2 p-2"
				>
					<ListHeaderItem :item="item" v-for="item in columns" />
				</ListHeader>

				<ListRows>
					<ListRow :row="row" v-for="row in labConnections.data">
						<template #default="{ column, item }">
							<ListRowItem :item="row[column.key]" :align="column.align">
								<div v-if="column.key === 'is_active'">
									<Badge v-if="row[column.key]" theme="green">
										{{ __('Active') }}
									</Badge>
									<Badge v-else theme="gray">
										{{ __('Inactive') }}
									</Badge>
								</div>
								<div v-else class="leading-5 text-sm">
									{{ row[column.key] }}
								</div>
							</ListRowItem>
						</template>
					</ListRow>
				</ListRows>

				<ListSelectBanner>
					<template #actions="{ unselectAll, selections }">
						<div class="flex gap-2">
							<Button
								variant="ghost"
								@click="removeConnection(selections, unselectAll)"
							>
								<Trash2 class="h-4 w-4 stroke-1.5" />
							</Button>
						</div>
					</template>
				</ListSelectBanner>
			</ListView>
		</div>
		<EmptyStateLayout
			v-else
			name="Lab Connections"
			:description="__('Add a remote Frappe/ERPNext system to get started.')"
			:icon="FlaskConical"
		/>
	</SettingsLayout>
	<LabConnectionForm
		v-else
		:connectionID="currentConnection"
		v-model:labConnections="labConnections"
		@updateStep="(step) => (view = step)"
	/>
</template>
<script setup>
import {
	Button,
	Badge,
	createListResource,
	ListView,
	ListHeader,
	ListHeaderItem,
	ListRows,
	ListRow,
	ListRowItem,
	ListSelectBanner,
	toast,
} from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'
import { Plus, Trash2, FlaskConical } from 'lucide-vue-next'
import { cleanError } from '@/utils'
import LabConnectionForm from '@/components/Settings/LabConnectionForm.vue'
import EmptyStateLayout from '@/components/Layouts/EmptyStateLayout.vue'
import SettingsLayout from '@/components/Layouts/SettingsLayout.vue'

const view = ref('list')
const currentConnection = ref(null)

const props = defineProps({
	label: String,
	description: String,
})

const labConnections = createListResource({
	doctype: 'LMS Lab Connection',
	fields: ['name', 'system_name', 'url', 'is_active'],
	cache: ['labConnections'],
})

onMounted(() => {
	labConnections.reload()
})

const openForm = (connectionID) => {
	currentConnection.value = connectionID
	view.value = 'form'
}

const removeConnection = (selections, unselectAll) => {
	Array.from(selections).forEach((id) => {
		labConnections.delete.submit(id, {
			onSuccess() {
				toast.success(__('Lab connection deleted'))
				labConnections.reload()
				unselectAll()
			},
			onError(err) {
				toast.error(cleanError(err?.messages?.[0] || err))
			},
		})
	})
}

const columns = computed(() => [
	{ label: __('Name'), key: 'system_name' },
	{ label: __('URL'), key: 'url' },
	{ label: __('Status'), key: 'is_active', align: 'center' },
])
</script>
