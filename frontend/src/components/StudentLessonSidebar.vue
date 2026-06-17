<template>
	<div class="flex flex-col h-full">
		<div class="bg-surface-gray-1 px-5 py-5 border-b">
			<div class="text-lg font-semibold text-ink-gray-9 leading-snug">
				{{ courseTitle }}
			</div>
			<div class="mt-4 flex items-center gap-2 text-sm text-ink-gray-7">
				<Cloud class="size-4 stroke-1.5" />
				<span>{{ __('Completed') }} {{ displayedProgress }}%</span>
			</div>
			<div
				class="h-1 w-full rounded-full bg-surface-gray-2 overflow-hidden mt-2"
			>
				<div
					class="h-full bg-surface-green-3 transition-all"
					:style="{ width: `${displayedProgress}%` }"
				/>
			</div>
		</div>

		<div class="flex-1 overflow-y-auto px-2 py-3">
			<Disclosure
				v-for="chapter in outline.data || []"
				:key="chapter.name"
				v-slot="{ open }"
				:defaultOpen="chapterDefaultOpen(chapter)"
			>
				<DisclosureButton
					class="w-full flex items-center justify-between rounded px-3 py-2 hover:bg-surface-gray-2 text-left"
				>
					<div
						class="flex items-center gap-2 text-sm font-medium text-ink-gray-9 min-w-0"
					>
						<ChevronDown
							class="size-4 stroke-1.5 shrink-0 transition-transform"
							:class="{ '-rotate-90': !open }"
						/>
						<span class="truncate">{{ chapter.title }}</span>
					</div>
					<span
						v-if="chapter.lessons?.length"
						class="text-xs text-ink-gray-5 shrink-0"
					>
						{{ chapter.lessons.length }}
					</span>
				</DisclosureButton>
				<DisclosurePanel>
					<component
						:is="inlineSelect ? 'div' : 'router-link'"
						v-for="lesson in chapter.lessons || []"
						:key="lesson.name"
						:to="
							inlineSelect
								? undefined
								: {
										name: 'Lesson',
										params: {
											courseName,
											chapterNumber: lesson.number.split('-')[0],
											lessonNumber: lesson.number.split('-')[1],
										},
								  }
						"
						class="flex items-center gap-2 rounded ps-9 pe-3 py-2 text-sm text-ink-gray-8 hover:bg-surface-gray-2"
						:class="[
							inlineSelect ? 'cursor-pointer' : '',
							isActive(lesson.number)
								? 'bg-surface-gray-2 text-ink-gray-9'
								: '',
						]"
						@click="
							inlineSelect &&
								emit('select-lesson', {
									chapterNumber: lesson.number.split('-')[0],
									lessonNumber: lesson.number.split('-')[1],
								})
						"
					>
						<component
							:is="iconFor(lesson)"
							class="size-4 stroke-1.5 shrink-0"
							:class="lesson.lab_id ? 'text-blue-500' : 'text-ink-gray-7'"
						/>
						<span class="truncate flex-1">{{ lesson.title }}</span>

						<!-- Lab status badge -->
						<template v-if="lesson.lab_id">
							<span
								v-if="labSubmissions[lesson.lab_id]"
								class="flex items-center gap-1 shrink-0 text-xs font-medium px-1.5 py-0.5 rounded-full"
								:class="labSubmissions[lesson.lab_id].status === 'Pass'
									? 'bg-green-100 text-green-700'
									: 'bg-red-100 text-red-600'"
							>
								<CheckCircle2
									v-if="labSubmissions[lesson.lab_id].status === 'Pass'"
									class="size-3"
								/>
								<XCircle v-else class="size-3" />
								{{ labSubmissions[lesson.lab_id].percentage.toFixed(0) }}%
							</span>
							<span
								v-else
								class="flex items-center gap-1 shrink-0 text-xs font-medium px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-500"
							>
								<FlaskConical class="size-3" />
								{{ __('Lab') }}
							</span>
						</template>

						<CircleCheck
							v-else-if="lesson.is_complete"
							class="size-4 stroke-1.5 shrink-0 text-green-700 fill-none"
						/>
						<Circle v-else class="size-4 stroke-1.5 shrink-0 text-ink-gray-4" />
					</component>
				</DisclosurePanel>
			</Disclosure>
		</div>
	</div>
</template>

<script setup>
import { computed, watch, watchEffect, ref, onMounted, onBeforeUnmount } from 'vue'
import { createResource, call } from 'frappe-ui'
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import {
	ChevronDown,
	Circle,
	CircleCheck,
	CheckCircle2,
	XCircle,
	Cloud,
	FileText,
	FlaskConical,
	HelpCircle,
	LockKeyhole,
	MonitorPlay,
	NotebookPen,
	SquareCode,
} from 'lucide-vue-next'

const props = defineProps({
	courseName: { type: String, required: true },
	courseTitle: { type: String, default: '' },
	progress: { type: Number, default: 0 },
	selectedLessonNumber: { type: String, default: '' },
	completedLesson: { type: String, default: null },
	inlineSelect: { type: Boolean, default: false },
	withProgress: { type: Boolean, default: true },
})

const emit = defineEmits(['select-lesson'])

const labSubmissions = ref({})

const outline = createResource({
	url: 'lms.lms.utils.get_course_outline',
	cache: [
		'course_outline_student',
		props.courseName,
		props.withProgress ? 'progress' : 'no-progress',
	],
	makeParams() {
		return {
			course: props.courseName,
			progress: props.withProgress,
		}
	},
	auto: true,
})

async function loadLabSubmissions() {
	if (!props.withProgress) return
	try {
		const data = await call('lms.lms.api.get_course_lab_submissions', {
			course: props.courseName,
		})
		labSubmissions.value = data || {}
	} catch {
		labSubmissions.value = {}
	}
}

// BroadcastChannel — odświeżenie submissions po zakończeniu cleanup w tle
let labChannel = null
let labResultPoller = null

function startLabResultPolling(labId) {
	if (labResultPoller) return
	const before = labSubmissions.value[labId]?.percentage
	labResultPoller = setInterval(async () => {
		await loadLabSubmissions()
		const after = labSubmissions.value[labId]?.percentage
		if (after !== undefined && after !== before) {
			clearInterval(labResultPoller)
			labResultPoller = null
		}
	}, 2000)
}

onMounted(() => {
	loadLabSubmissions()
	if (typeof BroadcastChannel !== 'undefined') {
		labChannel = new BroadcastChannel('lms_lab_results')
		labChannel.onmessage = (e) => {
			if (e.data?.type === 'lab_ended' && e.data.lab) {
				startLabResultPolling(e.data.lab)
			}
		}
	}
})

onBeforeUnmount(() => {
	if (labChannel) labChannel.close()
	if (labResultPoller) { clearInterval(labResultPoller); labResultPoller = null }
})

watch(
	() => props.courseName,
	() => {
		outline.reload()
		loadLabSubmissions()
	}
)

watchEffect(() => {
	const lessonName = props.completedLesson
	if (!lessonName || !outline.data) return
	for (const chapter of outline.data) {
		const found = chapter.lessons?.find((l) => l.name === lessonName)
		if (found) {
			found.is_complete = true
			return
		}
	}
})

const displayedProgress = computed(() => Math.ceil(props.progress || 0))

function iconFor(lesson) {
	if (lesson.lab_id) return FlaskConical
	switch (lesson.icon) {
		case 'icon-youtube':
			return MonitorPlay
		case 'icon-quiz':
			return HelpCircle
		case 'icon-assignment':
			return NotebookPen
		case 'icon-code':
			return SquareCode
		case 'icon-lock':
			return LockKeyhole
		default:
			return FileText
	}
}

function isActive(number) {
	return props.selectedLessonNumber === number
}

function chapterDefaultOpen(chapter) {
	if (!props.selectedLessonNumber) return chapter.idx === 1
	return (
		chapter.lessons?.some((l) => l.number === props.selectedLessonNumber) ||
		false
	)
}
</script>
