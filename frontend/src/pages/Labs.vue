<template>
	<PageHeader :breadcrumbs="breadcrumbs">
		<template #actions>
			<Button variant="solid" @click="showForm = true">
				<template #prefix>
					<Plus class="size-4 stroke-1.5" />
				</template>
				{{ __('Create') }}
			</Button>
		</template>
	</PageHeader>

	<div class="flex min-h-0 flex-1 flex-col pt-5">
		<div
			class="mx-5 mb-5 flex flex-col justify-between gap-y-4 sm:flex-row sm:items-center"
		>
			<div class="text-lg font-semibold text-ink-gray-9">
				{{ __('{0} Labs').format(labs.data?.length) }}
			</div>
			<FormControl v-model="search" type="text" :placeholder="__('Search')">
				<template #prefix>
					<FeatherIcon name="search" class="size-4 text-ink-gray-5" />
				</template>
			</FormControl>
		</div>
		<ListView
			v-if="labs.data?.length"
			:columns="columns"
			:rows="labs.data"
			row-key="name"
			:options="{ showTooltip: false, selectable: true }"
			class="flex-1 overflow-y-auto px-5"
		>
			<ListHeader
				class="mb-2 grid items-center rounded-none border-b bg-surface-white p-2"
			>
				<ListHeaderItem :item="item" v-for="item in columns" />
			</ListHeader>
			<ListRows>
				<router-link
					v-for="row in labs.data"
					:to="{ name: 'LabForm', params: { labID: row.name } }"
				>
					<ListRow :row="row" class="hover:bg-surface-gray-2">
						<template #default="{ column }">
							<ListRowItem
								:item="row[column.key]"
								:align="column.align"
							>
								<div class="text-sm leading-5">{{ row[column.key] }}</div>
							</ListRowItem>
						</template>
					</ListRow>
				</router-link>
			</ListRows>
			<ListSelectBanner>
				<template #actions="{ unselectAll, selections }">
					<div class="flex gap-2">
						<Button
							variant="ghost"
							@click="deleteLabs(selections, unselectAll)"
						>
							<FeatherIcon name="trash-2" class="h-4 w-4 stroke-1.5" />
						</Button>
					</div>
				</template>
			</ListSelectBanner>
		</ListView>
		<div v-else class="flex flex-1 items-center justify-center px-5">
			<EmptyStateLayout name="Labs" />
		</div>
	</div>

	<Dialog
		v-model="showForm"
		:options="{
			title: __('Create a Lab'),
			size: 'sm',
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					onClick({ close }) {
						insertLab(close)
					},
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<FormControl
					v-model="newTitle"
					:label="__('Title')"
					type="text"
					autocomplete="off"
					:required="true"
				/>
				<Link
					v-model="newConnection"
					:label="__('Lab Connection')"
					doctype="LMS Lab Connection"
				/>
			</div>
		</template>
	</Dialog>
</template>
<script setup>
import {
	Button,
	createListResource,
	Dialog,
	FeatherIcon,
	FormControl,
	ListView,
	ListRows,
	ListRow,
	ListRowItem,
	ListHeader,
	ListHeaderItem,
	ListSelectBanner,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { Plus } from 'lucide-vue-next'
import { useRouter, useRoute } from 'vue-router'
import { sessionStore } from '@/stores/session'
import EmptyStateLayout from '@/components/Layouts/EmptyStateLayout.vue'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import Link from '@/components/Controls/Link.vue'

const { brand } = sessionStore()
const user = inject('$user')
const router = useRouter()
const route = useRoute()
const search = ref('')
const showForm = ref(false)
const newTitle = ref('')
const newConnection = ref('')

onMounted(() => {
	if (!user.data?.is_moderator && !user.data?.is_instructor) {
		router.push({ name: 'Courses' })
	}
	if (route.query.new === 'true') {
		showForm.value = true
	}
})

watch(search, () => {
	labs.update({ filters: search.value ? { title: ['like', `%${search.value}%`] } : {} })
	labs.reload()
})

const labs = createListResource({
	doctype: 'LMS Lab',
	fields: ['name', 'title', 'lab_connection', 'passing_percentage', 'max_session_minutes', 'modified'],
	auto: true,
	orderBy: 'modified desc',
})

const insertLab = (close) => {
	if (!newTitle.value.trim()) {
		toast.warning(__('Title is required'))
		return
	}
	labs.insert.submit(
		{ title: newTitle.value.trim(), lab_connection: newConnection.value },
		{
			onSuccess(data) {
				toast.success(__('Lab created'))
				close()
				newTitle.value = ''
				newConnection.value = ''
				router.push({ name: 'LabForm', params: { labID: data.name } })
			},
			onError(err) {
				toast.error(err?.messages?.[0] || __('Error creating lab'))
			},
		}
	)
}

const deleteLabs = (selections, unselectAll) => {
	Array.from(selections).forEach(async (name) => {
		await labs.delete.submit(name)
	})
	unselectAll()
	toast.success(__('Labs deleted'))
}

const columns = computed(() => [
	{ label: __('Title'), key: 'title', width: 2 },
	{ label: __('Connection'), key: 'lab_connection', width: 1.5 },
	{ label: __('Passing %'), key: 'passing_percentage', width: 0.7, align: 'center' },
	{ label: __('Session (min)'), key: 'max_session_minutes', width: 0.7, align: 'center' },
])

const breadcrumbs = computed(() => [{ label: __('Labs'), route: { name: 'Labs' } }])

usePageMeta(() => ({ title: __('Labs'), icon: brand.favicon }))
</script>
