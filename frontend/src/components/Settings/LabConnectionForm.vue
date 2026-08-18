<template>
	<SettingsLayout
		:title="title"
		:description="__('Configure an external Frappe/ERPNext system where lab environments will be provisioned.')"
		:show-back="true"
		@back="emit('updateStep', 'list')"
	>
		<template #header-actions>
			<Button variant="ghost" @click="testConnection" :loading="testing">
				{{ __('Test Connection') }}
			</Button>
			<Button variant="solid" @click="save">{{ __('Save') }}</Button>
		</template>
		<div class="grid grid-cols-2 gap-5">
			<FormControl
				v-model="connection.system_name"
				:label="__('System Name')"
				type="text"
				:required="true"
			/>
			<FormControl
				v-model="connection.url"
				:label="__('System URL')"
				type="text"
				placeholder="https://test.example.com"
				:required="true"
			/>
			<FormControl
				v-model="connection.api_key"
				:label="__('Admin API Key')"
				type="text"
				:required="true"
			/>
			<FormControl
				v-model="connection.api_secret"
				:label="__('Admin API Secret')"
				type="password"
				:required="true"
			/>
			<div class="col-span-2">
				<Switch
					size="sm"
					v-model="connection.is_active"
					:label="__('Active')"
					:description="__('Enable this connection for lab provisioning.')"
				/>
			</div>
		</div>
	</SettingsLayout>
</template>
<script setup>
import { Button, FormControl, call, toast } from 'frappe-ui'
import Switch from '@/components/Controls/BooleanSwitch.vue'
import { computed, reactive, watch, ref } from 'vue'
import { cleanError } from '@/utils'
import SettingsLayout from '@/components/Layouts/SettingsLayout.vue'

const emit = defineEmits(['updateStep'])
const labConnections = defineModel('labConnections')
const testing = ref(false)

const connection = reactive({
	name: '',
	system_name: '',
	url: '',
	api_key: '',
	api_secret: '',
	is_active: true,
})

const props = defineProps({
	connectionID: String,
})

const title = computed(() =>
	props.connectionID === 'new'
		? __('New Lab Connection')
		: __('Edit Lab Connection')
)

watch(
	() => props.connectionID,
	(val) => {
		if (val === 'new') {
			connection.name = ''
			connection.system_name = ''
			connection.url = ''
			connection.api_key = ''
			connection.api_secret = ''
			connection.is_active = true
		} else if (val) {
			const existing = labConnections.value?.data?.find((c) => c.name === val)
			if (existing) {
				connection.name = existing.name
				connection.system_name = existing.system_name
				connection.url = existing.url
				connection.api_key = existing.api_key || ''
				connection.api_secret = ''
				connection.is_active = !!existing.is_active
			}
		}
	},
	{ immediate: true }
)

const save = () => {
	if (props.connectionID === 'new') {
		createConnection()
	} else {
		updateConnection()
	}
}

const createConnection = () => {
	labConnections.value?.insert.submit(
		{ ...connection },
		{
			onSuccess() {
				labConnections.value?.reload()
				emit('updateStep', 'list')
				toast.success(__('Lab connection created'))
			},
			onError(err) {
				toast.error(cleanError(err?.messages?.[0] || err) || __('Error creating lab connection'))
			},
		}
	)
}

const updateConnection = () => {
	const payload = { ...connection }
	if (!payload.api_secret) delete payload.api_secret

	labConnections.value?.setValue.submit(
		{ ...payload, name: props.connectionID },
		{
			onSuccess() {
				labConnections.value?.reload()
				emit('updateStep', 'list')
				toast.success(__('Lab connection updated'))
			},
			onError(err) {
				toast.error(cleanError(err?.messages?.[0] || err) || __('Error updating lab connection'))
			},
		}
	)
}

const testConnection = async () => {
	if (!connection.url || !connection.api_key || !connection.api_secret) {
		toast.warning(__('Fill in URL, API Key, and API Secret first'))
		return
	}
	testing.value = true
	try {
		await call('lms.lms.doctype.lms_lab_connection.lms_lab_connection.test_connection_params', {
			url: connection.url,
			api_key: connection.api_key,
			api_secret: connection.api_secret,
		})
		toast.success(__('Connection successful'))
	} catch (err) {
		toast.error(cleanError(err?.messages?.[0] || err) || __('Connection failed'))
	} finally {
		testing.value = false
	}
}
</script>
