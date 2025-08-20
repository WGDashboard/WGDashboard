<script setup>
import dayjs from "dayjs";
import {computed, ref} from "vue";
import {fetchGet, fetchPost, getUrl} from "@/utilities/fetch.js";
import {useRoute} from "vue-router";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import LocaleText from "@/components/text/localeText.vue";
const props = defineProps(["b", "delay"])
const deleteConfirmation = ref(false)
const restoreConfirmation = ref(false)
const route = useRoute()
const emit = defineEmits(["refresh", "refreshPeersList"])
const store = DashboardConfigurationStore()
const loading = ref(false);
const deleteBackup = () => {
	loading.value = true;
	fetchPost("/api/deleteWireguardConfigurationBackup", {
		ConfigurationName: route.params.id,
		BackupFileName: props.b.filename
	}, (res) => {
		loading.value = false;
		if (res.status){
			emit("refresh")
			store.newMessage("Server", "Backup deleted", "success")
		}else{
			store.newMessage("Server", "Backup failed to delete", "danger")
		}
	})
}

const restoreBackup = () => {
	loading.value = true;
	fetchPost("/api/restoreWireguardConfigurationBackup", {
		ConfigurationName: route.params.id,
		BackupFileName: props.b.filename
	}, (res) => {
		loading.value = false;
		restoreConfirmation.value = false;
		if (res.status){
			emit("refreshPeersList")
			store.newMessage("Server", "Backup restored with " + props.b.filename, "success")
		}else{
			store.newMessage("Server", "Backup failed to restore", "danger")
		}
	})
}

const downloadBackup = () => {
	fetchGet("/api/downloadWireguardConfigurationBackup", {
		configurationName: route.params.id,
		backupFileName: props.b.filename
	}, (res) => {
		if (res.status){
			window.open(getUrl(`/fileDownload?file=${res.data}`), '_blank')
		}
	})
}

const delaySeconds = computed(() => {
	return props.delay + 's'
})

const showContent = ref(false);
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
							        :disabled="loading"
							        @click='deleteBackup()'>
								<LocaleText t="Yes"></LocaleText>
							</button>
							<button
								@click="deleteConfirmation = false"
								:disabled="loading"
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
								:disabled="loading"
								@click="restoreBackup()"
								class="btn btn-success rounded-3">
								<LocaleText t="Yes"></LocaleText>
							</button>
							<button
								@click="restoreConfirmation = false"
								:disabled="loading"
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
						@click="downloadBackup()"
						class="btn bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-3 btn-sm">
						<i class="bi bi-download"></i>
					</button>
					<button 
						@click="restoreConfirmation = true"
						class="btn bg-warning-subtle text-warning-emphasis border-warning-subtle rounded-3 btn-sm">
						<i class="bi bi-clock-history"></i>
					</button>
					<button 
						@click="deleteConfirmation = true"
						class="btn bg-danger-subtle text-danger-emphasis border-danger-subtle rounded-3 btn-sm">
						<i class="bi bi-trash-fill"></i>
					</button>
				</div>
			</div>
			<hr>
			<div class="card rounded-3">
				<a role="button" class="card-header d-flex text-decoration-none align-items-center" 
				   :class="{'border-bottom-0': !showContent}"
				   style="cursor: pointer" @click="showContent = !showContent">
					<small>.conf <LocaleText t="File"></LocaleText>
						</small>
					<i class="bi bi-chevron-down ms-auto"></i>
				</a>
				<div class="card-body" v-if="showContent">
					<textarea class="form-control rounded-3" :value="b.content"
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