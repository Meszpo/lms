<template>
	<div v-if="lesson.data" class="">
		<PageHeader :breadcrumbs="breadcrumbs">
			<template #actions>
				<CertificationLinks :courseName="courseName" />
				<router-link
					v-if="canEditLesson"
					:to="{
						name: 'CourseDetail',
						params: { courseName: courseName },
						hash: '#editor',
						query: { editLesson: `${chapterNumber}-${lessonNumber}` },
					}"
				>
					<HeaderButton :label="__('Editor View')" icon="lucide-pencil" />
				</router-link>
			</template>
		</PageHeader>

		<div
			v-if="isMobile && lessonTotal"
			class="flex items-center gap-2 border-b bg-surface-base px-5 py-2.5"
		>
			<Button
				variant="subtle"
				class="!size-9"
				:label="__('Previous lesson')"
				:disabled="!hasPrev"
				@click="goPrev()"
			>
				<template #icon>
					<span class="lucide-chevron-left size-4" />
				</template>
			</Button>
			<div
				class="min-w-0 flex-1 text-center text-p-xs font-medium tabular-nums text-ink-gray-5"
			>
				{{ lessonIndex }} / {{ lessonTotal }}
			</div>
			<Button
				variant="subtle"
				class="!size-9"
				:label="__('Next lesson')"
				:disabled="!hasNext"
				@click="goNext()"
			>
				<template #icon>
					<span class="lucide-chevron-right size-4" />
				</template>
			</Button>
		</div>

		<div class="grid md:grid-cols-[70%,30%] sm:h-[94vh]">
			<div v-if="lesson.data.no_preview" class="sm:border-e">
				<div class="shadow rounded-md w-3/4 mt-10 mx-auto text-center p-4">
					<div class="flex items-center justify-center mt-4 gap-x-2">
						<span class="lucide-lock-keyhole size-4 text-ink-gray-5" />
						<div class="text-lg-semibold text-ink-gray-7">
							{{ __('This lesson is locked') }}
						</div>
					</div>
					<div class="mt-1 mb-4 text-ink-gray-7">
						{{
							__(
								'This lesson is not available for preview. Please enroll in the course to access it.'
							)
						}}
					</div>
					<Button
						v-if="user.data && !lesson.data.disable_self_learning"
						@click="enrollStudent()"
						variant="solid"
					>
						{{ __('Start Learning') }}
					</Button>
					<Badge
						theme="blue"
						size="lg"
						v-else-if="lesson.data.disable_self_learning"
						class="mt-2"
					>
						{{ __('Contact the Administrator to enroll for this course.') }}
					</Badge>
					<Button v-else @click="redirectToLogin()">
						<template #prefix>
							<span class="lucide-log-in size-4" />
						</template>
						{{ __('Login') }}
					</Button>
				</div>
			</div>
			<div
				v-else
				ref="lessonContainer"
				class="bg-surface-base min-w-0"
				:class="{
					'overflow-y-auto': zenModeEnabled,
				}"
			>
				<div
					class="sm:border-e pt-8 sm:pt-5 pb-10 h-full"
					:class="{
						'w-full md:w-3/5 mx-auto border-none !pt-10': zenModeEnabled,
					}"
				>
					<div class="px-5">
						<div
							class="flex flex-col space-y-3 md:space-y-0 md:flex-row md:items-center justify-between"
						>
							<div class="flex flex-col">
								<h1 class="text-4xl-semibold text-ink-gray-9">
									{{ lesson.data.title }}
								</h1>

								<div
									v-if="zenModeEnabled"
									class="relative flex items-center gap-x-2 text-sm text-ink-gray-7 group w-fit mt-2"
								>
									<span>
										{{ lesson.data.chapter_title }} -
										{{ lesson.data.course_title }}
									</span>
									<span class="lucide-info size-3" />
									<div
										class="hidden group-hover:block rounded bg-surface-gray-10 px-2 py-1 text-xs text-ink-base shadow-xl absolute start-0 top-full mt-2"
									>
										{{ Math.ceil(lesson.data.membership.progress) }}%
										{{ __('completed') }}
									</div>
								</div>
							</div>

							<div
								v-if="!zenModeEnabled && !isMobile"
								class="flex items-center gap-x-2 mt-2 md:mt-0"
							>
								<Tooltip v-if="canGoZen()" :text="__('Zen Mode')">
									<Button @click="goFullScreen()" :label="__('Zen Mode')">
										<template #icon>
											<span class="lucide-focus size-4" />
										</template>
									</Button>
								</Tooltip>
								<Button v-if="lesson.data.prev" @click="switchLesson('prev')">
									<template #prefix>
										<span class="lucide-chevron-left size-4" />
									</template>
									<span>{{ __('Previous') }}</span>
								</Button>
								<Button v-if="lesson.data.next" @click="switchLesson('next')">
									<template #suffix>
										<span class="lucide-chevron-right size-4" />
									</template>
									<span>{{ __('Next') }}</span>
								</Button>
								<router-link
									v-else
									:to="{
										name: 'CourseDetail',
										params: { courseName: courseName },
									}"
								>
									<Button class="text-p-base-medium">{{
										__('Back to Course')
									}}</Button>
								</router-link>
							</div>

							<div
								v-if="zenModeEnabled"
								class="flex items-center gap-x-2 mt-2 md:mt-0"
							>
								<Button
									@click="showDiscussionsInZenMode()"
									:label="__('Toggle discussions')"
								>
									<template #icon>
										<span class="lucide-message-circle-question size-4" />
									</template>
								</Button>
								<Button v-if="lesson.data.prev" @click="switchLesson('prev')">
									<template #prefix>
										<span class="lucide-chevron-left size-4" />
									</template>
									<span>
										{{ __('Previous') }}
									</span>
								</Button>

								<Button v-if="lesson.data.next" @click="switchLesson('next')">
									<template #suffix>
										<span class="lucide-chevron-right size-4" />
									</template>
									<span>
										{{ __('Next') }}
									</span>
								</Button>

								<router-link
									v-else
									:to="{
										name: 'CourseDetail',
										params: { courseName: courseName },
									}"
								>
									<Button class="text-p-base-medium">
										{{ __('Back to Course') }}
									</Button>
								</router-link>
							</div>
						</div>

						<div v-if="!zenModeEnabled" class="flex items-center mt-4 md:mt-2">
							<span
								class="h-6 me-1"
								:class="{
									'avatar-group overlap': lesson.data.instructors?.length > 1,
								}"
							>
								<UserAvatar
									v-for="instructor in lesson.data.instructors"
									:key="instructor.name ?? instructor"
									:user="instructor"
								/>
							</span>
							<CourseInstructors
								v-if="lesson.data?.instructors"
								:instructors="lesson.data.instructors"
							/>
						</div>

						<div
							v-if="
								lesson.data.instructor_content &&
								JSON.parse(lesson.data.instructor_content)?.blocks?.length >
									1 &&
								allowInstructorContent()
							"
							class="bg-surface-gray-2 p-3 rounded-md mt-6"
						>
							<h2 class="text-ink-gray-5 font-medium">
								{{ __('Instructor Notes') }}
							</h2>
							<div
								id="instructor-content"
								class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal"
							></div>
						</div>
						<div
							v-else-if="lesson.data.instructor_notes"
							class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal mt-8"
						>
							<LessonContent :content="lesson.data.instructor_notes" />
						</div>
						<div
							v-if="lesson.data.content"
							@mouseup="toggleInlineMenu"
							class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal mt-8"
						>
							<div id="editor"></div>
						</div>
						<div
							v-else
							class="ProseMirror prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-outline-gray-2 prose-th:border-outline-gray-2 prose-td:relative prose-th:relative prose-th:bg-surface-gray-2 prose-sm max-w-none !whitespace-normal mt-8"
						>
							<LessonContent
								v-if="lesson.data?.body"
								:content="lesson.data.body"
								:youtube="lesson.data.youtube"
								:quizId="lesson.data.quiz_id"
							/>
						</div>

						<!-- Interactive Lab section -->
						<div v-if="lesson.data?.lab_id" class="mt-8 mx-5">
							<div class="border rounded-lg p-5 bg-surface-blue-1 border-outline-blue-2">
								<div class="flex items-center gap-2 mb-2">
									<FlaskConical class="size-5 text-ink-blue-3 stroke-1.5" />
									<h3 class="font-semibold text-ink-gray-8">{{ __('Interactive Lab') }}</h3>
								</div>
								<div
									v-if="labInfo?.description"
									class="text-sm text-ink-gray-6 mb-4 lab-desc-preview"
									v-html="renderLabDesc(labInfo.description)"
								></div>
								<p v-else class="text-sm text-ink-gray-6 mb-4">
									{{ __('This lesson includes an interactive lab. You will work in a live Frappe/ERPNext environment and your work will be automatically evaluated.') }}
								</p>
								<div
									v-if="labInfo?.max_attempts"
									class="text-sm text-ink-gray-6 mb-3"
								>
									{{ __('Attempts remaining: {0} of {1}').format(labInfo.remaining_attempts, labInfo.max_attempts) }}
								</div>
								<div
									v-if="labSessionBusy && !selectedLabSubmission"
									class="text-sm text-ink-gray-6 mb-3 flex items-center gap-2"
								>
									<span class="inline-block size-3.5 border-2 border-ink-blue-3 border-t-transparent rounded-full animate-spin shrink-0"></span>
									<span>
										{{ labSessionStatus === 'Evaluating'
											? __('Evaluating your lab…')
											: __('Cleaning up lab environment…') }}
									</span>
								</div>
								<div
									v-else-if="labSessionBusy && selectedLabSubmission"
									class="text-xs text-ink-gray-5 mb-3 flex items-center gap-2"
								>
									<span class="inline-block size-3 border-2 border-ink-gray-4 border-t-transparent rounded-full animate-spin shrink-0"></span>
									<span>{{ __('Cleaning up lab environment…') }}</span>
								</div>
								<div
									v-if="labSubmissions.length > 1"
									class="flex items-center justify-between mb-3"
								>
									<span class="text-xs text-ink-gray-5">
										{{ __('Attempt {0} of {1}').format(
											labSubmissions.length - selectedSubmissionIndex,
											labSubmissions.length,
										) }}
									</span>
									<div class="flex items-center gap-1">
										<Button
											variant="ghost"
											size="sm"
											:disabled="selectedSubmissionIndex >= labSubmissions.length - 1"
											@click="selectOlderSubmission"
										>
											<template #icon><ChevronLeft class="size-4" /></template>
										</Button>
										<Button
											variant="ghost"
											size="sm"
											:disabled="selectedSubmissionIndex <= 0"
											@click="selectNewerSubmission"
										>
											<template #icon><ChevronRight class="size-4" /></template>
										</Button>
									</div>
								</div>
								<LabSubmissionResult
									v-if="selectedLabSubmission"
									:submission="selectedLabSubmission"
								/>
								<p
									v-if="!canStartLab && !labSessionBusy"
									class="text-sm text-ink-red-3 mb-2"
								>
									{{ __('You have used all available attempts for this lab.') }}
								</p>
								<Button
									variant="solid"
									:disabled="labCleaning || !canStartLab"
									@click="openLabWindow"
									class="mt-2"
								>
									<template #prefix><FlaskConical class="size-4" /></template>
									{{ selectedLabSubmission ? __('Retry Lab') : __('Start Lab') }}
								</Button>
							</div>
						</div>
					</div>
					<div
						v-if="lesson.data && (allowDiscussions || tabs.length > 1)"
						class="mt-10 pb-20 pt-5 border-t px-5"
						ref="discussionsContainer"
					>
						<TabButtons
							v-if="tabs.length > 1"
							:options="tabs"
							v-model="currentTab"
							class="w-fit mb-10"
						/>
						<Notes
							v-if="currentTab === 'Notes'"
							:lesson="lesson.data?.name"
							v-model:notes="notes"
							@updateNotes="updateNotes"
						/>
						<Discussions
							v-else-if="allowDiscussions"
							:title="'Questions'"
							:doctype="'Course Lesson'"
							:docname="lesson.data.name"
							:key="lesson.data.name"
							:emptyStateText="
								__('Ask a question to get help from the community.')
							"
						/>
					</div>
				</div>
			</div>
			<aside v-if="!isMobile" class="sticky top-10 h-[94vh]">
				<StudentLessonSidebar
					:courseName="courseName"
					:courseTitle="lesson.data.course_title"
					:progress="lessonProgress"
					:selectedLessonNumber="`${chapterNumber}-${lessonNumber}`"
					:completedLesson="completedLesson"
				/>
			</aside>
		</div>

		<div
			v-if="isMobile"
			class="pointer-events-none sticky bottom-4 z-10 flex justify-end px-4"
		>
			<Button
				variant="outline"
				class="pointer-events-auto !h-11 !rounded-full !px-4 !shadow-lg"
				@click="showChapters = true"
			>
				<template #prefix>
					<span class="lucide-layers size-4" />
				</template>
				{{ __('Chapters') }}
			</Button>
		</div>

		<BottomSheet v-if="isMobile" v-model="showChapters">
			<template #header>
				<div class="min-w-0 truncate text-p-lg-semibold text-ink-gray-9">
					{{ lesson.data.course_title }}
				</div>
			</template>
			<StudentLessonSidebar
				:courseName="courseName"
				:progress="lessonProgress"
				:selectedLessonNumber="`${chapterNumber}-${lessonNumber}`"
				:completedLesson="completedLesson"
				:hideHeader="true"
				@select-lesson="showChapters = false"
			/>
		</BottomSheet>
	</div>
	<InlineLessonMenu
		v-if="lesson.data?.name"
		v-model="showInlineMenu"
		:lesson="lesson.data?.name"
		v-model:notes="notes"
		@updateNotes="updateNotes"
	/>
	<VideoStatistics
		v-if="isAdmin"
		v-model="showStatsDialog"
		:lessonName="lesson.data?.name"
		:lessonTitle="lesson.data?.title"
	/>

	<!-- Popup permission dialog -->
	<Teleport to="body">
		<Transition name="lms-dialog-fade">
			<div
				v-if="showPopupDialog"
				class="fixed inset-0 z-50 flex items-center justify-center p-4"
				style="background: rgba(0,0,0,0.45)"
				@click.self="showPopupDialog = false"
			>
				<div class="bg-white rounded-xl shadow-2xl w-full max-w-md p-6">
					<div class="flex items-start gap-4 mb-5">
						<div class="shrink-0 flex items-center justify-center w-10 h-10 rounded-full bg-blue-50">
							<AppWindow class="size-5 text-blue-600" />
						</div>
						<div>
							<h3 class="font-semibold text-gray-900 text-base mb-1">
								{{ __('Allow opening new windows') }}
							</h3>
							<p class="text-sm text-gray-600 leading-relaxed">
								{{ __('This lab requires opening 2 browser windows: one for the lab system and one for the instructions panel. Please allow pop-ups for this site if your browser asks.') }}
							</p>
						</div>
					</div>
					<div
						v-if="popupBlocked"
						class="mb-4 flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2.5"
					>
						<AlertCircle class="size-4 text-red-500 shrink-0 mt-0.5" />
						<p class="text-sm text-red-700">
							{{ __('Pop-ups are blocked by your browser. Please allow pop-ups for this site in your browser settings and try again.') }}
						</p>
					</div>
					<div class="flex justify-end gap-2">
						<button
							class="px-4 py-2 text-sm font-medium text-gray-600 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
							@click="showPopupDialog = false"
						>{{ __('Cancel') }}</button>
						<button
							class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
							@click="confirmAndOpenLab"
						>{{ __('Allow & Start Lab') }}</button>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>
<script setup>
import {
	Badge,
	Button,
	call,
	createListResource,
	createResource,
	TabButtons,
	Tooltip,
	usePageMeta,
	toast,
} from 'frappe-ui'
import {
	computed,
	watch,
	inject,
	ref,
	onMounted,
	onBeforeUnmount,
	nextTick,
} from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
	ChevronLeft,
	ChevronRight,
	LockKeyholeIcon,
	LogIn,
	Focus,
	Info,
	MessageCircleQuestion,
	TrendingUp,
	FlaskConical,
	AppWindow,
	AlertCircle,
} from 'lucide-vue-next'
import {
	getEditorTools,
	enablePlyr,
	highlightText,
	sanitizeEditorJs,
} from '@/utils'
import { sessionStore } from '@/stores/session'
import { useSidebar } from '@/stores/sidebar'
import { useSettings } from '@/stores/settings'
import { useScreenSize } from '@/utils/composables'
import {
	resolveDwellSeconds,
	isVideoComplete,
	shouldStartDwellTimer,
	shouldAttachVideoFallback,
} from '@/utils/lessonProgress'
import EditorJS from '@editorjs/editorjs'
import LessonContent from '@/components/LessonContent.vue'
import CourseInstructors from '@/components/CourseInstructors.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import Discussions from '@/components/Discussions.vue'
import CertificationLinks from '@/components/CertificationLinks.vue'
import CourseOutline from '@/components/CourseOutline.vue'
import StudentLessonSidebar from '@/components/StudentLessonSidebar.vue'
import BottomSheet from '@/components/BottomSheet.vue'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import Notes from '@/components/Notes/Notes.vue'
import InlineLessonMenu from '@/components/Notes/InlineLessonMenu.vue'
import LabSubmissionResult from '@/components/LabSubmissionResult.vue'
import VideoStatistics from '@/components/Modals/VideoStatistics.vue'
import { getLmsRoute } from '@/utils/basePath'
import { provideStudentView } from '@/composables/useStudentView'

const router = useRouter()
const route = useRoute()
const realUser = inject('$user')
// A component's own provide() is invisible to its own inject(), so read the
// handles provideStudentView returns rather than calling useStudentView().
const { isStudentView, mockedUser } = provideStudentView(
	realUser,
	() => route.query.studentView === '1'
)
// Shadows every user.data read below and in every child, so the page renders
// exactly what a student sees.
const user = mockedUser
const socket = inject('$socket')
const allowDiscussions = ref(false)
const editor = ref(null)
const instructorEditor = ref(null)
const lessonProgress = ref(0)
const lessonContainer = ref(null)
const zenModeEnabled = ref(false)
const showStatsDialog = ref(false)
const showPopupDialog = ref(false)
const popupBlocked = ref(false)
const hasQuiz = ref(false)
const discussionsContainer = ref(null)
const timer = ref(0)
const { brand } = sessionStore()
const sidebarStore = useSidebar()
const plyrSources = ref([])
const showInlineMenu = ref(false)
const currentTab = ref(null)
const completedLesson = ref(null)
const settingsStore = useSettings()
const { isMobile } = useScreenSize()
const showChapters = ref(false)
let timerInterval = null

const tabs = ref([])

const props = defineProps({
	courseName: {
		type: String,
		required: true,
	},
	chapterNumber: {
		type: String,
		required: true,
	},
	lessonNumber: {
		type: String,
		required: true,
	},
})

let collapsedByLesson = false
const isCourseAdmin = () =>
	Boolean(user.data?.is_moderator || user.data?.is_instructor)

onMounted(() => {
	startTimer()
	// Keep the app sidebar open for admins/instructors so they can navigate
	// while reviewing; only collapse it for students to maximise reading space.
	if (!isCourseAdmin()) {
		sidebarStore.isSidebarCollapsed = true
		collapsedByLesson = true
	}
	document.addEventListener('fullscreenchange', attachFullscreenEvent)
	socket.on('update_lesson_progress', (data) => {
		if (data.course === props.courseName) {
			lessonProgress.value = data.progress
		}
	})
	if (typeof BroadcastChannel !== 'undefined') {
		labBroadcastChannel = new BroadcastChannel('lms_lab_results')
		labBroadcastChannel.onmessage = (e) => {
			if (
				e.data?.type === 'lab_evaluated' &&
				e.data.lab === lesson.data?.lab_id
			) {
				onLabEvaluated()
			} else if (
				e.data?.type === 'lab_ended' &&
				e.data.lab === lesson.data?.lab_id
			) {
				labEndedAt = new Date()
				labEndedLastSubmissionName = selectedLabSubmission.value?.name || null
				labCleaning.value = true
				startResultPolling()
				startCleanupPolling()
			}
		}
	}
	socket.on('lab_evaluated', (data) => {
		if (data.lab === lesson.data?.lab_id && data.lesson === lesson.data?.name) {
			onLabEvaluated()
		}
	})
})

const attachFullscreenEvent = () => {
	if (document.fullscreenElement) {
		zenModeEnabled.value = true
		allowDiscussions.value = false
	} else {
		zenModeEnabled.value = false
		if (!hasQuiz.value) {
			allowDiscussions.value = true
		}
	}
}

onBeforeUnmount(() => {
	document.removeEventListener('fullscreenchange', attachFullscreenEvent)
	if (collapsedByLesson) sidebarStore.isSidebarCollapsed = false
	trackVideoWatchDuration()
	if (labBroadcastChannel) labBroadcastChannel.close()
	socket.off('lab_evaluated')
	if (labCleanupPoller) { clearInterval(labCleanupPoller); labCleanupPoller = null }
	if (labResultPoller) { clearInterval(labResultPoller); labResultPoller = null }
})

const lesson = createResource({
	url: 'lms.lms.utils.get_lesson',
	makeParams(values) {
		return {
			course: props.courseName,
			chapter: values ? values.chapter : props.chapterNumber,
			lesson: values ? values.lesson : props.lessonNumber,
		}
	},
	auto: true,
})

const setupLesson = (data) => {
	if (Object.keys(data).length === 0) {
		router.push({
			name: 'CourseDetail',
			params: { courseName: props.courseName },
		})
		return
	}
	if (data.is_scorm_package) {
		router.push({
			name: 'SCORMChapter',
			params: {
				courseName: props.courseName,
				chapterName: data.chapter_name,
			},
		})
	}
	lessonProgress.value = data.membership?.progress
	if (data.content) editor.value = renderEditor('editor', data.content)
	if (
		data.instructor_content &&
		JSON.parse(data.instructor_content)?.blocks?.length > 1
	)
		instructorEditor.value = renderEditor(
			'instructor-content',
			data.instructor_content
		)
	editor.value?.isReady.then(() => {
		checkIfDiscussionsAllowed()
	})
	checkQuiz()
	loadLabSubmissions()
	loadLabInfo()
	checkLabCleanupStatus()
}

const checkQuiz = () => {
	if (!editor.value && lesson.body) {
		const quizRegex = /\{\{ Quiz\(".*"\) \}\}/
		hasQuiz.value = quizRegex.test(lesson.body)
		if (!hasQuiz.value && !zenModeEnabled) {
			allowDiscussions.value = true
		} else {
			allowDiscussions.value = false
		}
	}
}

const renderEditor = (holder, content) => {
	if (document.getElementById(holder))
		document.getElementById(holder).innerHTML = ''
	return new EditorJS({
		holder: holder,
		tools: getEditorTools(false, {}, { studentView: isStudentView.value }),
		data: sanitizeEditorJs(JSON.parse(content)),
		readOnly: true,
		defaultBlock: 'embed',
		i18n: {
			direction: document.documentElement.dir === 'rtl' ? 'rtl' : 'ltr',
		},
		onReady() {
			const root = document.getElementById(holder)
			if (!root) return
			root.querySelectorAll('a').forEach((a) => {
				a.setAttribute('target', '_blank')
				a.setAttribute('rel', 'noopener noreferrer')
			})
		},
	})
}

// Video-ended fires markProgress + trackVideoWatchDuration in parallel,
// and trackVideoWatchDuration's getPlyrSourceDetails calls markProgress
// again. Without an in-flight guard the two save_progress requests race
// and the second one fails with TimestampMismatchError on LMS Enrollment.
let progressSubmitting = false
const markProgress = () => {
	if (progressSubmitting) return
	// Only enrolled students record progress; a moderator previewing has no
	// membership row so save_progress would no-op server-side but still
	// flip the in-memory `completedLesson` and show a green tick that
	// vanishes on refresh.
	if (
		!user.data ||
		!lesson.data ||
		!lesson.data.membership ||
		lesson.data.progress
	)
		return
	progressSubmitting = true
	progress.submit(
		{},
		{
			onSuccess() {
				progressSubmitting = false
			},
			onError(err) {
				progressSubmitting = false
				console.error(err)
			},
		}
	)
}

const progress = createResource({
	url: 'lms.lms.doctype.course_lesson.course_lesson.save_progress',
	makeParams() {
		return {
			lesson: lesson.data.name,
			course: props.courseName,
		}
	},
	onSuccess(data) {
		lessonProgress.value = data
		completedLesson.value = lesson.data?.name
	},
})

const notes = createListResource({
	doctype: 'LMS Lesson Note',
	filters: {
		lesson: lesson.data?.name,
		member: user.data?.name,
	},
	fields: ['name', 'color', 'highlighted_text', 'note'],
	onSuccess(data) {
		data.forEach((note) => {
			setTimeout(() => {
				highlightText(note)
			}, 500)
		})
	},
})

const breadcrumbs = computed(() => {
	let crumbs = [{ label: __('Courses'), route: { name: 'Courses' } }]
	crumbs.push({
		label: lesson?.data?.course_title,
		route: { name: 'CourseDetail', params: { courseName: props.courseName } },
	})
	crumbs.push({
		label: lesson?.data?.title,
		route: {
			name: 'Lesson',
			params: {
				courseName: props.courseName,
				chapterNumber: props.chapterNumber,
				lessonNumber: props.lessonNumber,
			},
			query: studentViewQuery.value,
		},
	})
	return crumbs
})

const outline = createResource({
	url: 'lms.lms.utils.get_course_outline',
	cache: ['course_outline_student', props.courseName, 'progress'],
	makeParams() {
		return {
			course: props.courseName,
			progress: true,
		}
	},
	auto: false,
})
outline.fetch()

watch(
	() => props.courseName,
	() => outline.reload()
)

const lessonNumbers = computed(() =>
	(outline.data ?? []).flatMap((c) => c.lessons?.map((l) => l.number) ?? [])
)
const currentIndex = computed(() =>
	lessonNumbers.value.indexOf(`${props.chapterNumber}-${props.lessonNumber}`)
)
const lessonTotal = computed(() => lessonNumbers.value.length)
const lessonIndex = computed(() =>
	currentIndex.value >= 0 ? currentIndex.value + 1 : 0
)
const hasPrev = computed(() => currentIndex.value > 0)
const hasNext = computed(
	() => currentIndex.value >= 0 && currentIndex.value < lessonTotal.value - 1
)

const goToLessonNumber = (number) => {
	trackVideoWatchDuration()
	const [chapterNumber, lessonNumber] = number.split('-')
	router.push({
		name: 'Lesson',
		params: {
			courseName: props.courseName,
			chapterNumber,
			lessonNumber,
		},
		query: studentViewQuery.value,
	})
}

const goPrev = () => {
	if (hasPrev.value)
		goToLessonNumber(lessonNumbers.value[currentIndex.value - 1])
}

const goNext = () => {
	if (hasNext.value)
		goToLessonNumber(lessonNumbers.value[currentIndex.value + 1])
}

const switchLesson = (direction) => {
	trackVideoWatchDuration()
	let target =
		direction === 'prev'
			? lesson.data.prev.split('.')
			: lesson.data.next.split('.')

	const [chapterNumber, lessonNumber] = target
	router.push({
		name: 'Lesson',
		params: {
			courseName: props.courseName,
			chapterNumber,
			lessonNumber,
		},
		query: studentViewQuery.value,
	})
}

watch(
	[() => route.params.chapterNumber, () => route.params.lessonNumber],
	async (
		[newChapterNumber, newLessonNumber],
		[oldChapterNumber, oldLessonNumber]
	) => {
		if (newChapterNumber || newLessonNumber) {
			plyrSources.value = []
			await nextTick()
			resetLessonState(newChapterNumber, newLessonNumber)
			updateNotes()
			checkIfDiscussionsAllowed()
			checkQuiz()
		}
	}
)

const resetLessonState = (newChapterNumber, newLessonNumber) => {
	editor.value = null
	instructorEditor.value = null
	allowDiscussions.value = false
	lesson.submit({
		chapter: newChapterNumber,
		lesson: newLessonNumber,
	})
	videoFallbackArmed = false
	fallbackGeneration++
	clearInterval(timerInterval)
	timer.value = 0
}

const trackVideoWatchDuration = () => {
	if (!lesson.data?.membership) return
	let videoDetails = getVideoDetails()
	videoDetails = videoDetails.concat(getPlyrSourceDetails())
	call('lms.lms.api.track_video_watch_duration', {
		lesson: lesson.data.name,
		videos: videoDetails,
	})
}

const getVideoDetails = () => {
	let details = []
	const videos = document.querySelectorAll('video')
	if (videos.length > 0) {
		videos.forEach((video) => {
			if (isVideoComplete(video.currentTime, video.duration)) markProgress()
			details.push({
				source: video.src,
				watch_time: video.currentTime,
			})
		})
	}
	return details
}

const getPlyrSourceDetails = () => {
	let details = []
	plyrSources.value.forEach((source) => {
		if (isVideoComplete(source.currentTime, source.duration)) markProgress()
		let src = cleanYouTubeUrl(source.source)
		details.push({
			source: src,
			watch_time: source.currentTime,
		})
	})
	return details
}

const cleanYouTubeUrl = (url) => {
	if (!url) return url
	const urlObj = new URL(url)
	urlObj.searchParams.delete('t')
	return urlObj.toString()
}

watch(
	() => lesson.data,
	async (data) => {
		setupLesson(data)
		// Settings drive dwell + enforcement; if they haven't resolved yet
		// the timer reads undefined and falls back to 30s. Await the
		// resource so the admin-configured dwell time wins from the first
		// lesson load.
		if (settingsStore.settings?.promise) {
			try {
				await settingsStore.settings.promise
			} catch {}
		}
		startTimer()
		await getPlyrSource()
		updateNotes()
		const hasVideoListener =
			plyrSources.value.length > 0 || !!document.querySelector('video')
		const enforceVideo = Number(
			settingsStore.settings?.data?.enforce_video_completion ?? 0
		)
		// When the lesson has video AND enforcement is on, suppress dwell so
		// completion is gated on play-to-end. When enforcement is off, dwell
		// runs for every lesson type (including YouTube/Plyr), so admins can
		// set a short dwell to mark video lessons complete without a full
		// playthrough.
		if (!shouldStartDwellTimer({ hasVideo: hasVideoListener, enforceVideo })) {
			clearInterval(timerInterval)
		}
		if (
			shouldAttachVideoFallback({ hasVideo: hasVideoListener, enforceVideo })
		) {
			document.querySelectorAll('video').forEach((video) => {
				if (video._lmsErrorAttached) return
				video._lmsErrorAttached = true
				const gen = fallbackGeneration
				video.addEventListener(
					'error',
					() => {
						if (gen !== fallbackGeneration) return
						fallbackToDwellTimer('html5-video-error')
					},
					{ once: true }
				)
			})
		}
	}
)

const getPlyrSource = async () => {
	await nextTick()
	if (plyrSources.value.length == 0) {
		plyrSources.value = await enablePlyr()
		const enforceVideo = Number(
			settingsStore.settings?.data?.enforce_video_completion ?? 0
		)
		if (
			shouldAttachVideoFallback({
				hasVideo: plyrSources.value.length > 0,
				enforceVideo,
			})
		) {
			plyrSources.value.forEach((player) => {
				let readyFired = false
				const gen = fallbackGeneration
				player.on('ready', () => {
					readyFired = true
				})
				player.on('error', (event) => {
					if (gen !== fallbackGeneration) return
					fallbackToDwellTimer(
						'plyr-error: ' + (event?.detail?.message || 'unknown')
					)
				})
				setTimeout(() => {
					if (!readyFired && gen === fallbackGeneration) {
						fallbackToDwellTimer('plyr-no-ready-15s')
					}
				}, 15000)
			})
		}
	}
	updateVideoWatchDuration()
}

const updateVideoWatchDuration = () => {
	if (lesson.data.videos && lesson.data.videos.length > 0) {
		lesson.data.videos.forEach((video) => {
			if (video.source.includes('youtube') || video.source.includes('vimeo')) {
				updatePlyrVideoTime(video)
			} else {
				updateVideoTime(video)
			}
		})
	}
	attachVideoEndedListeners()
}

const attachVideoEndedListeners = () => {
	const onVideoEnded = () => {
		markProgress()
		trackVideoWatchDuration()
	}

	document.querySelectorAll('video').forEach((video) => {
		if (!video._lmsEndedAttached) {
			video.addEventListener('ended', onVideoEnded)
			video._lmsEndedAttached = true
		}
	})

	plyrSources.value.forEach((plyrSource) => {
		if (!plyrSource._lmsEndedAttached) {
			plyrSource.on('ended', onVideoEnded)
			plyrSource.on('statechange', (event) => {
				if (event.detail?.code === 0) onVideoEnded()
			})
			plyrSource._lmsEndedAttached = true
		}
	})
}

const updatePlyrVideoTime = (video) => {
	plyrSources.value.forEach((plyrSource) => {
		let lastWatchedTime = 0
		let isSeeking = false

		plyrSource.on('ready', () => {
			if (plyrSource.source === video.source) {
				plyrSource.embed.seekTo(video.watch_time, true)
				plyrSource.play()
				plyrSource.pause()
			}
		})
	})
}

const updateVideoTime = (video) => {
	const videos = document.querySelectorAll('video')
	if (videos.length > 0) {
		videos.forEach((vid) => {
			if (vid.src === video.source) {
				let watch_time = video.watch_time < vid.duration ? video.watch_time : 0
				if (vid.readyState >= 1) {
					vid.currentTime = watch_time
				} else {
					vid.addEventListener('loadedmetadata', () => {
						vid.currentTime = watch_time
					})
				}
			}
		})
	}
}

let videoFallbackArmed = false
let fallbackGeneration = 0
const fallbackToDwellTimer = (reason) => {
	// The dwell fallback only matters for an enrolled student tracking progress.
	// Don't surface the "mark as viewed" toast in student view or to
	// non-enrolled viewers (admins/instructors reviewing the lesson).
	if (isStudentView.value || !lesson.data?.membership) return
	if (videoFallbackArmed) return
	videoFallbackArmed = true
	console.warn('[Lesson] video fallback engaged:', reason)
	toast.warning(
		__(
			'Video failed to load. This lesson will still be marked complete after you spend some time on it.'
		)
	)
	clearInterval(timerInterval)
	timer.value = 0
	startTimer()
}

const startTimer = () => {
	if (!lesson.data?.membership) return
	const dwell = resolveDwellSeconds(
		settingsStore.settings?.data?.lesson_dwell_time
	)
	if (dwell === null) return
	if (dwell === 0) {
		markProgress()
		return
	}
	timerInterval = setInterval(() => {
		timer.value++
		if (timer.value >= dwell) {
			clearInterval(timerInterval)
			markProgress()
		}
	}, 1000)
}

onBeforeUnmount(() => {
	clearInterval(timerInterval)
})

const checkIfDiscussionsAllowed = () => {
	hasQuiz.value = false
	if (lesson.data?.content) {
		try {
			JSON.parse(lesson.data.content)?.blocks?.forEach((block) => {
				if (block.type === 'quiz') {
					hasQuiz.value = true
				}
			})
		} catch {
			// legacy markdown lessons
		}
	}

	if (
		!hasQuiz.value &&
		!zenModeEnabled.value &&
		(lesson.data?.membership ||
			user.data?.is_moderator ||
			user.data?.is_instructor)
	) {
		allowDiscussions.value = true
	} else {
		allowDiscussions.value = false
	}
}

const isAdmin = computed(() => {
	let isInstructor = lesson.data?.instructors?.includes(user.data?.name)
	return user.data?.is_moderator || isInstructor
})

// Student view is a mode, not a destination: every hop that stays on a lesson
// has to carry the flag, or Prev / Next / the sidebar silently drops the
// moderator back into their own identity mid-course.
const studentViewQuery = computed(() =>
	isStudentView.value ? { studentView: 1 } : undefined
)

// Reads the real user, not the student-view shadow, so the way back to the
// editor survives ?studentView=1.
const canEditLesson = computed(() => {
	const isInstructor = lesson.data?.instructors?.includes(realUser.data?.name)
	return realUser.data?.is_moderator || isInstructor
})

const allowInstructorContent = () => {
	if (window.read_only_mode) return false
	return isAdmin.value
}

const enrollment = createResource({
	url: 'frappe.client.insert',
	makeParams() {
		return {
			doc: {
				doctype: 'LMS Enrollment',
				course: props.courseName,
				member: user.data?.name,
			},
		}
	},
})

const enrollStudent = () => {
	enrollment.submit(
		{},
		{
			onSuccess() {
				window.location.reload()
			},
			onError(err) {
				toast.error(__(err.messages?.[0] || err))
				console.error(err)
			},
		}
	)
}

const toggleInlineMenu = async () => {
	showInlineMenu.value = false
	await nextTick()
	let selection = window.getSelection()
	if (selection.toString()) {
		showInlineMenu.value = true
	}
}

const showVideoStats = () => {
	showStatsDialog.value = true
}

// Interactive Lab
const labSubmissions = ref([])
const selectedSubmissionIndex = ref(0)
const selectedLabSubmission = computed(
	() => labSubmissions.value[selectedSubmissionIndex.value] || null,
)
const labInfo = ref(null)
const labCleaning = ref(false)
const labSessionStatus = ref(null)
let labCleanupPoller = null
let labResultPoller = null
let labBroadcastChannel = null
let labEndedAt = null
let labEndedLastSubmissionName = null

const canStartLab = computed(() => {
	if (!labInfo.value?.max_attempts) return true
	if (labInfo.value.remaining_attempts === null) return true
	return labInfo.value.remaining_attempts > 0
})

const labSessionBusy = computed(() => labCleaning.value)

const selectNewerSubmission = () => {
	if (selectedSubmissionIndex.value > 0) selectedSubmissionIndex.value -= 1
}

const selectOlderSubmission = () => {
	if (selectedSubmissionIndex.value < labSubmissions.value.length - 1) {
		selectedSubmissionIndex.value += 1
	}
}

const markLabLessonComplete = async () => {
	const name = lesson.data?.name
	if (name) {
		completedLesson.value = name
	}
	try {
		const updated = await call(
			'lms.lms.doctype.course_lesson.course_lesson.save_progress',
			{ lesson: lesson.data.name, course: props.courseName },
		)
		if (updated) {
			lessonProgress.value = updated
		}
	} catch {}
}

const handleNewSubmission = async (sub) => {
	if (!sub || sub.name === labEndedLastSubmissionName) return false
	selectedSubmissionIndex.value = 0
	if (sub.status === 'Pass') {
		await markLabLessonComplete()
	}
	await loadLabInfo()
	return true
}

const pollEvaluationResult = async () => {
	await loadLabSubmissions()
	return handleNewSubmission(labSubmissions.value[0])
}

const startResultPolling = async () => {
	if (labResultPoller) return
	const done = await pollEvaluationResult()
	if (done) return
	labResultPoller = setInterval(async () => {
		const done = await pollEvaluationResult()
		if (done) {
			clearInterval(labResultPoller)
			labResultPoller = null
		}
	}, 2000)
}

const onLabEvaluated = async () => {
	await loadLabSubmissions()
	selectedSubmissionIndex.value = 0
	await loadLabInfo()
	const sub = labSubmissions.value[0]
	if (sub?.status === 'Pass') {
		await markLabLessonComplete()
	}
}

const pollCleanupOnce = async () => {
	const labId = lesson.data?.lab_id
	if (!labId) return true
	try {
		const res = await call('lms.lms.api.get_lab_cleanup_status', {
			lab: labId,
			include_active: true,
		})
		labSessionStatus.value = res?.status || null
		if (res?.status === 'Evaluating') {
			await pollEvaluationResult()
		}
		if (!res?.cleaning) {
			labCleaning.value = false
			labSessionStatus.value = null
			if (labCleanupPoller) { clearInterval(labCleanupPoller); labCleanupPoller = null }
			await loadLabInfo()
			return true
		}
		labCleaning.value = true
	} catch {}
	return false
}

const startCleanupPolling = async () => {
	if (labCleanupPoller) return
	// Check immediately — job may already be done
	const done = await pollCleanupOnce()
	if (done) return
	labCleanupPoller = setInterval(async () => {
		await pollCleanupOnce()
	}, 2000)
}

const checkLabCleanupStatus = async () => {
	if (!lesson.data?.lab_id) return
	try {
		const res = await call('lms.lms.api.get_lab_cleanup_status', {
			lab: lesson.data.lab_id,
			include_active: true,
		})
		labCleaning.value = res?.cleaning || false
		labSessionStatus.value = res?.status || null
		if (labCleaning.value) {
			startResultPolling()
			startCleanupPolling()
		}
	} catch {
		labCleaning.value = false
		labSessionStatus.value = null
	}
}

const loadLabInfo = async () => {
	if (!lesson.data?.lab_id) return
	try {
		labInfo.value = await call('lms.lms.api.get_lab_info', {
			lab: lesson.data.lab_id,
			lesson: lesson.data.name,
		})
	} catch {
		labInfo.value = null
	}
}

function renderLabDesc(text) {
	if (!text) return ''
	const lines = text.split('\n')
	const out = []
	let inUl = false, inOl = false
	function closeList() {
		if (inUl) { out.push('</ul>'); inUl = false }
		if (inOl) { out.push('</ol>'); inOl = false }
	}
	function inline(s) {
		return s
			.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
			.replace(/\*([^*\n]+)\*/g, '<em>$1</em>')
			.replace(/`([^`\n]+)`/g, '<code>$1</code>')
			.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
	}
	for (const line of lines) {
		const h1 = line.match(/^# (.+)$/), h2 = line.match(/^## (.+)$/), h3 = line.match(/^### (.+)$/)
		const ul = line.match(/^[*-] (.+)$/), ol = line.match(/^\d+\. (.+)$/)
		if (h1) { closeList(); out.push(`<h1>${inline(h1[1])}</h1>`) }
		else if (h2) { closeList(); out.push(`<h2>${inline(h2[1])}</h2>`) }
		else if (h3) { closeList(); out.push(`<h3>${inline(h3[1])}</h3>`) }
		else if (line.match(/^---+$/)) { closeList(); out.push('<hr>') }
		else if (ul) {
			if (inOl) { out.push('</ol>'); inOl = false }
			if (!inUl) { out.push('<ul>'); inUl = true }
			out.push(`<li>${inline(ul[1])}</li>`)
		} else if (ol) {
			if (inUl) { out.push('</ul>'); inUl = false }
			if (!inOl) { out.push('<ol>'); inOl = true }
			out.push(`<li>${inline(ol[1])}</li>`)
		} else if (line.trim() === '') { closeList() }
		else { closeList(); out.push(`<p>${inline(line)}</p>`) }
	}
	closeList()
	return out.join('\n')
}

const loadLabSubmissions = async () => {
	if (!lesson.data?.lab_id) return
	try {
		const data = await call('lms.lms.api.get_lab_submissions', {
			lab: lesson.data.lab_id,
			lesson: lesson.data.name,
		})
		labSubmissions.value = data || []
		if (selectedSubmissionIndex.value >= labSubmissions.value.length) {
			selectedSubmissionIndex.value = 0
		}
	} catch {
		labSubmissions.value = []
		selectedSubmissionIndex.value = 0
	}
}

const openLabWindow = () => {
	popupBlocked.value = false
	showPopupDialog.value = true
}

const confirmAndOpenLab = () => {
	const courseName = route.params.courseName || ''
	const panelUrl = getLmsRoute(`/labs/${lesson.data.lab_id}/${lesson.data.name}?course=${courseName}`)
	const panelW = 400
	const screenH = window.screen.availHeight
	const screenW = window.screen.availWidth
	const labW = Math.max(screenW - panelW - 8, 800)
	const monitorLeft = window.screenX
	const monitorTop = window.screenY

	// Test whether browser allows popups before committing — open blank window first.
	const testWin = window.open('', '_blank', 'width=1,height=1,left=-9999,top=-9999')
	if (!testWin || testWin.closed) {
		popupBlocked.value = true
		return
	}
	testWin.close()

	showPopupDialog.value = false

	// Open both windows in the same call stack so popup blocker allows both.
	const sysWin = window.open('', 'lms_lab_system',
		`width=${labW},height=${screenH},left=${monitorLeft},top=${monitorTop},resizable=yes`)
	if (sysWin) {
		sysWin.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>Starting lab environment…</title><style>*{margin:0;padding:0;box-sizing:border-box}body{display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui,sans-serif;background:#f8fafc;color:#374151}.wrap{text-align:center}.spinner{width:52px;height:52px;border:4px solid #e5e7eb;border-top-color:#3b82f6;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 20px}@keyframes spin{to{transform:rotate(360deg)}}h1{font-size:1.1rem;font-weight:600;color:#111827;margin-bottom:8px}p{font-size:.875rem;color:#6b7280;line-height:1.5}</style></head><body><div class="wrap"><div class="spinner"></div><h1>Starting lab environment…</h1><p>Please wait. The system will open automatically.</p></div></body></html>`)
		sysWin.document.close()
	}
	const sep = panelUrl.includes('?') ? '&' : '?'
	const panelUrlWithMeta = `${panelUrl}${sep}monitorLeft=${monitorLeft}&monitorTop=${monitorTop}`
	window.open(panelUrlWithMeta, 'lms_lab_panel',
		`width=${panelW},height=${screenH},left=${monitorLeft + labW + 8},top=${monitorTop},resizable=no,scrollbars=yes`)
}

const canGoZen = () => {
	if (
		user.data?.is_moderator ||
		user.data?.is_instructor ||
		user.data?.is_evaluator
	)
		return true
	if (lesson.data?.membership) return true
	return false
}

const goFullScreen = () => {
	if (lessonContainer.value.requestFullscreen) {
		lessonContainer.value.requestFullscreen()
	} else if (lessonContainer.value.mozRequestFullScreen) {
		lessonContainer.value.mozRequestFullScreen()
	} else if (lessonContainer.value.webkitRequestFullscreen) {
		lessonContainer.value.webkitRequestFullscreen()
	} else if (lessonContainer.value.msRequestFullscreen) {
		lessonContainer.value.msRequestFullscreen()
	}
}

const showDiscussionsInZenMode = () => {
	if (allowDiscussions.value) {
		allowDiscussions.value = false
	} else {
		allowDiscussions.value = true
		currentTab.value = 'Community'
		scrollDiscussionsIntoView()
	}
}

const scrollDiscussionsIntoView = () => {
	nextTick(() => {
		discussionsContainer.value?.scrollIntoView({
			behavior: 'smooth',
			block: 'center',
			inline: 'nearest',
		})
	})
}

const updateNotes = () => {
	if (!user.data) return
	notes.update({
		filters: {
			lesson: lesson.data?.name,
			member: user.data?.name,
		},
	})
	notes.reload()
}

watch(allowDiscussions, () => {
	if (!isAdmin.value) {
		if (!tabs.value.find((tab) => tab.value === 'Notes')) {
			tabs.value.push({
				label: __('Notes'),
				value: 'Notes',
			})
		}
		currentTab.value = 'Notes'
	} else {
		currentTab.value = allowDiscussions.value ? 'Community' : null
	}
	if (allowDiscussions.value) {
		if (!tabs.value.find((tab) => tab.value === 'Community')) {
			tabs.value.push({
				label: __('Community'),
				value: 'Community',
			})
		}
	}
})

const redirectToLogin = () => {
	window.location.href = `/login?redirect-to=${getLmsRoute(
		`courses/${props.courseName}`
	)}`
}

usePageMeta(() => {
	return {
		title: lesson?.data?.title,
		icon: brand.favicon,
	}
})
</script>
<style>
.avatar-group {
	display: inline-flex;
	align-items: center;
}

.avatar-group .avatar {
	transition: margin 0.1s ease-in-out;
}

.lesson-content p {
	margin-bottom: 1rem;
	line-height: 1.7;
}

.lesson-content li {
	line-height: 1.7;
}

.lesson-content ol {
	list-style: auto;
	margin: revert;
	padding: 1rem;
}

.lesson-content ul {
	list-style: auto;
	padding: 1rem;
	margin: revert;
}

.lesson-content img {
	border: 1px solid theme('colors.gray.200');
	border-radius: 0.5rem;
}

.lesson-content code {
	display: block;
	overflow-x: auto;
	padding: 1rem 1.25rem;
	background: #011627;
	color: #d6deeb;
	border-radius: 0.5rem;
	margin: 1rem 0;
}

.lesson-content a {
	color: theme('colors.gray.900');
	text-decoration: underline;
	font-weight: 500;
}

.lab-desc-preview h2 {
	font-size: 0.8125rem;
	font-weight: 600;
	color: var(--ink-gray-8, #1f2937);
	margin-top: 0.875rem;
	margin-bottom: 0.25rem;
}

.lab-desc-preview h2:first-child {
	margin-top: 0;
}

.lab-desc-preview p {
	margin-bottom: 0.4rem;
	line-height: 1.6;
}

.lab-desc-preview ul,
.lab-desc-preview ol {
	padding-left: 1.25rem;
	margin-bottom: 0.4rem;
}

.lab-desc-preview ul { list-style-type: disc; }
.lab-desc-preview ol { list-style-type: decimal; }

.lab-desc-preview li {
	margin-bottom: 0.15rem;
	line-height: 1.5;
}

.lab-desc-preview code {
	background: rgba(0,0,0,0.06);
	border-radius: 3px;
	padding: 0.1em 0.3em;
	font-size: 0.8em;
}

.embed-tool__caption,
.cdx-simple-image__caption {
	display: none;
}

.ce-block__content {
	max-width: unset;
}

.codex-editor b,
.codex-editor strong {
	font-weight: bold;
}

.codex-editor i,
.codex-editor em {
	font-style: italic;
}

.codex-editor u {
	text-decoration: underline;
}

.codex-editor s {
	text-decoration: line-through;
}

.codex-editor__redactor {
	padding-bottom: 0px !important;
}

.codeBoxHolder {
	display: flex;
	flex-direction: column;
	justify-content: flex-start;
	align-items: flex-start;
}

.codeBoxTextArea {
	width: 100%;
	min-height: 30px;
	padding: 10px;
	border-radius: 2px 2px 2px 0;
	border: none !important;
	outline: none !important;
	font: 14px monospace;
}

.codeBoxSelectDiv {
	display: flex;
	flex-direction: column;
	justify-content: flex-start;
	align-items: flex-start;
	position: relative;
}

.codeBoxSelectInput {
	border-radius: 0 0 20px 2px;
	padding: 2px 26px;
	padding-top: 0;
	padding-inline-end: 0;
	text-align: start;
	cursor: pointer;
	border: none !important;
	outline: none !important;
}

.codeBoxSelectDropIcon {
	position: absolute !important;
	inset-inline-start: 10px !important;
	bottom: 0 !important;
	width: unset !important;
	height: unset !important;
	font-size: 16px !important;
}

.codeBoxSelectPreview {
	display: none;
	flex-direction: column;
	justify-content: flex-start;
	align-items: flex-start;
	border-radius: 2px;
	box-shadow: 0 3px 15px -3px rgba(13, 20, 33, 0.13);
	position: absolute;
	top: 100%;
	margin: 5px 0;
	max-height: 30vh;
	overflow-x: hidden;
	overflow-y: auto;
	z-index: 10000;
}

.codeBoxSelectItem {
	width: 100%;
	padding: 5px 20px;
	margin: 0;
	cursor: pointer;
}

.codeBoxSelectItem:hover {
	opacity: 0.7;
}

.codeBoxSelectedItem {
	background-color: lightblue !important;
}

.codeBoxShow {
	display: flex !important;
}

.dark {
	color: #abb2bf;
	background-color: #282c34;
}

.light {
	color: #383a42;
	background-color: #fafafa;
}

.codeBoxTextArea {
	line-height: 1.7;
}

.tc-table {
	border-inline-start: 1px solid #e8e8eb;
}

.plyr__volume input[type='range'] {
	display: none;
}

.plyr__control--overlaid {
	background: radial-gradient(
		circle,
		rgba(0, 0, 0, 0.4) 0%,
		rgba(0, 0, 0, 0.5) 50%
	);
}

.plyr__control:hover {
	background: none;
}

.plyr--video {
	border: 1px solid theme('colors.gray.200');
	border-radius: 8px;
}

:root {
	--plyr-range-fill-background: white;
	--plyr-video-control-background-hover: transparent;
}

.lms-dialog-fade-enter-active,
.lms-dialog-fade-leave-active {
	transition: opacity 0.2s ease;
}
.lms-dialog-fade-enter-active > div,
.lms-dialog-fade-leave-active > div {
	transition: opacity 0.2s ease, transform 0.2s ease;
}
.lms-dialog-fade-enter-from,
.lms-dialog-fade-leave-to {
	opacity: 0;
}
.lms-dialog-fade-enter-from > div,
.lms-dialog-fade-leave-to > div {
	opacity: 0;
	transform: scale(0.96) translateY(8px);
}
</style>
