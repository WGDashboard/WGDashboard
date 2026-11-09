<script setup>
import dayjs from "dayjs";
import {computed, ref} from "vue";
import {fetchBackup, getUrl} from "@/utilities/fetch.js";
import {useRoute} from "vue-router";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import LocaleText from "@/components/text/localeText.vue";
const props = defineProps(["b", "delay", "busy"])
const deleteConfirmation = ref(false)
const restoreConfirmation = ref(false)
const route = useRoute()
const emit = defineEmits(["refresh", "refreshPeersList"])
const store = DashboardConfigurationStore()
const loading = ref(false);
const backupParams = () => ({configurationName: route.params.id, backupFileName: props.b.filename})
const backupBody = () => ({ConfigurationName: route.params.id, BackupFileName: props.b.filename})

const deleteBackup = async () => {
	loading.value = true
	try {
		await fetchBackup("/api/deleteWireguardConfigurationBackup", {}, backupBody())
		emit("refresh")
		store.newMessage("Server", "Backup deleted", "success")
	} catch (err) {
		store.newMessage("Server", err.message, "danger")
	} finally {
		loading.value = false
		deleteConfirmation.value = false
	}
}

const restoreBackup = async () => {
	loading.value = true
	try {
		await fetchBackup("/api/restoreWireguardConfigurationBackup", {}, backupBody())
		emit("refreshPeersList")
		store.newMessage("Server", "Backup restored with " + props.b.filename, "success")
	} catch (err) {
		store.newMessage("Server", err.message, "danger")
	} finally {
		loading.value = false
		restoreConfirmation.value = false
	}
}

const downloadBackup = () => {
	window.location.href = getUrl(`/api/downloadWireguardConfigurationBackup?${new URLSearchParams(backupParams())}`)
}

const delaySeconds = computed(() => {
	return props.delay + 's'
})

const showContent = ref(false)
const content = ref(null)
const previewError = ref("")

const toggleContent = async () => {
	showContent.value = !showContent.value
	if (!showContent.value || content.value !== null) return
	previewError.value = ""
	try {
		content.value = await fetchBackup("/api/getWireguardConfigurationBackupContent", backupParams())
	} catch (err) {
		previewError.value = err.message
	}
}
</script>
 
<template>
	<div class="card my-0 rounded-3">
		<div class="card-body position-relative">
			<Transition name="zoomReversed">
				<div 
					v-if="deleteConfirmation"
					class="position-absolute w-100 h-100 confirmationContainer start-0 top-0 rounded-3 d-flex p-2">
					<div class="m-auto">
						<h5>
							<LocaleText t="Are you sure to delete this backup?"></LocaleText>
						</h5>
						<div class="d-flex gap-2 align-items-center justify-content-center">
							<button class="btn btn-danger rounded-3" 
							        :disabled="loading || busy"
							        @click='deleteBackup()'>
								<LocaleText t="Yes"></LocaleText>
							</button>
							<button
								@click="deleteConfirmation = false"
								:disabled="loading || busy"
								class="btn bg-secondary-subtle text-secondary-emphasis border-secondary-subtle rounded-3">
								<LocaleText t="No"></LocaleText>
							</button>
						</div>
					</div>
				</div>
			</Transition>
			<Transition name="zoomReversed">
				<div
					v-if="restoreConfirmation"
					class="position-absolute w-100 h-100 confirmationContainer start-0 top-0 rounded-3 d-flex p-2">
					<div class="m-auto">
						<h5>
							<LocaleText t="Are you sure to restore this backup?"></LocaleText>
						</h5>
						<div class="d-flex gap-2 align-items-center justify-content-center">
							<button
								:disabled="loading || busy"
								@click="restoreBackup()"
								class="btn btn-success rounded-3">
								<LocaleText t="Yes"></LocaleText>
							</button>
							<button
								@click="restoreConfirmation = false"
								:disabled="loading || busy"
								class="btn bg-secondary-subtle text-secondary-emphasis border-secondary-subtle rounded-3">
								<LocaleText t="No"></LocaleText>
							</button>
						</div>
					</div>
				</div>
			</Transition>
			<div class="d-flex gap-3">
				<div class="d-flex flex-column">
					<small class="text-muted">
						<LocaleText t="Backup"></LocaleText>
					</small>
					<samp>{{b.filename}}</samp>
				</div>
				<div class="d-flex flex-column">
					<small class="text-muted">
						<LocaleText t="Backup Date"></LocaleText>
					</small>
					{{dayjs(b.backupDate, "YYYYMMDDHHmmss").format("YYYY-MM-DD HH:mm:ss")}}
				</div>
				<div class="d-flex gap-2 align-items-center ms-auto">
				<button
						@click="downloadBackup()" :disabled="busy || loading"
						class="btn bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-3 btn-sm">
						<i class="bi bi-download"></i>
					</button>
					<button 
						@click="restoreConfirmation = true" :disabled="busy || loading"
						class="btn bg-warning-subtle text-warning-emphasis border-warning-subtle rounded-3 btn-sm">
						<i class="bi bi-clock-history"></i>
					</button>
					<button 
						@click="deleteConfirmation = true" :disabled="busy || loading"
						class="btn bg-danger-subtle text-danger-emphasis border-danger-subtle rounded-3 btn-sm">
						<i class="bi bi-trash-fill"></i>
					</button>
				</div>
			</div>
			<hr>
			<div class="card rounded-3">
				<a role="button" class="card-header d-flex text-decoration-none align-items-center" 
				   :class="{'border-bottom-0': !showContent}"
				   style="cursor: pointer" @click="toggleContent()">
					<small>.conf <LocaleText t="File"></LocaleText>
						</small>
					<i class="bi bi-chevron-down ms-auto"></i>
				</a>
				<div class="card-body" v-if="showContent">
					<div v-if="previewError" class="text-danger" role="alert">{{previewError}}</div>
					<div v-else-if="content === null" class="spinner-border spinner-border-sm" role="status"></div>
					<textarea v-else class="form-control rounded-3" :value="content"
					          disabled
					          style="height: 300px; font-family: var(--bs-font-monospace),sans-serif !important;"></textarea>
				</div>
			</div>
			<hr>
			<div class="d-flex">
				<span>
					<i class="bi bi-database me-1"></i>
					<LocaleText t="Database File"></LocaleText>
				</span>
				<i class="bi ms-auto"
					:class="[b.database ? 'text-success bi-check-circle-fill' : 'text-danger bi-x-circle-fill']"
				></i>
			</div>
			
			
		</div>
	</div>
</template>

<style scoped>
.confirmationContainer{
	background-color: rgba(0, 0, 0, 0.53);
	z-index: 9999;
	backdrop-filter: blur(1px);
	-webkit-backdrop-filter: blur(1px);
}

.list1-enter-active{
	transition-delay: v-bind(delaySeconds) !important;
}
</style>