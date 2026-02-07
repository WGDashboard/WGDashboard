<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {computed, onMounted, reactive, ref, watch} from "vue";
import CodeEditor from "@/utilities/simple-code-editor/CodeEditor.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {initSystemThemeWatcher, resolveTheme} from "@/utilities/theme.js";
const allowedFileType = ref("conf")
const fileUploader = ref(undefined)

const uploadFiles = reactive({
	conf: undefined,
	sql: undefined
})

const dashboardStore = DashboardConfigurationStore();
const editorTheme = computed(() => {
	return resolveTheme(dashboardStore.Configuration.Server.dashboard_theme) === "dark" ? "github-dark" : "github";
});

onMounted(() => {
	initSystemThemeWatcher();
	fileUploader.value = document.querySelector("#fileUploader");
	fileUploader.value.addEventListener("change", (e) => {
		uploadFiles[allowedFileType.value] = undefined;
		const files = e.target.files;
		const reader = new FileReader();
		reader.onload = (evt) => {
			uploadFiles[allowedFileType.value] = {
				filename: files[0].name,
				content: evt.target.result
			}
		}
		reader.readAsText(files[0])
	})
})

const openFilePicker = (fileType) => {
	allowedFileType.value = fileType;
	setTimeout(() => {
		fileUploader.value.click()
	}, 100)
}

const resetInput = (t) => {
	uploadFiles[t] = undefined; 
	document.querySelector('form').reset()
}

watch(uploadFiles, () => {
	if(uploadFiles.conf !== undefined && uploadFiles.sql !== undefined){
		if (uploadFiles.conf.filename.replace('.conf', '') !== uploadFiles.sql.filename.replace('.sql', '')){
			dashboardStore.newMessage("WGDashboard", 
				"Backup configuration filename not matching database filename", "danger")
		}
	}
}, {
	deep: true
})

const fileNameValidation = computed(() => {
	if (uploadFiles.conf !== undefined){
		
	}
})

const uploadReady = computed(() => {
	return uploadFiles.conf !== undefined 
		&& uploadFiles.sql !== undefined
})

</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container-fluid d-flex h-100 w-100">
			<div class="m-auto mt-0 modal-dialog-centered dashboardModal w-100">
				<div class="card rounded-3 shadow flex-grow-1 w-100">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4">
						<h4 class="mb-0">
							<LocaleText t="Upload Backup"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="this.$emit('close')"></button>
					</div>
					<div class="card-body px-4 pb-4 d-flex flex-column gap-2">
						<form class="d-none">
							<input type="file" id="fileUploader" class="d-none" :accept="'.' + allowedFileType" />
						</form>
						<div class="row g-2">
							<div class="col-12" v-for="t in ['conf', 'sql']">
								<div class="card rounded-3">
									<div class="card-header d-flex align-items-center">
										<span class="h5 mb-0 opacity-50 me-2">
											<i class="bi bi-file-earmark-fill"></i>
										</span>
										<LocaleText t="Configuration File" v-if="t === 'conf'"></LocaleText>
										<LocaleText t="Database File" v-else></LocaleText>
										<div class="ms-auto d-flex gap-1">
											<button
												v-if="uploadFiles[t]"
												@click="resetInput(t)"
												class="ms-auto btn text-secondary-emphasis bg-secondary-subtle rounded-3 border-1 border-secondary-subtle d-flex align-items-center">
												<i class="bi bi-x-lg me-2"></i>
												<LocaleText t="Clear"></LocaleText>
											</button>
											<button
												@click="openFilePicker(t)"
												class="ms-auto text-decoration-none btn text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle d-flex align-items-center">
												<i class="bi bi-folder2-open me-2"></i>
												<LocaleText t="Open File"></LocaleText>
											</button>
										</div>
									</div>
									<div class="card-body">
										<div v-if="uploadFiles[t]" class="d-flex flex-column gap-2">
											<CodeEditor
												:disabled="true"
												:read-only="true"
												:display-language="true"
												v-model="uploadFiles[t].content"
												:theme="editorTheme"
												:languages="[[t, uploadFiles[t].filename]]"
												width="100%" height="500px">
											</CodeEditor>
										</div>
										<p class="text-center mb-0 text-muted" v-else>
											<LocaleText t="No file opened"></LocaleText>
										</p>
									</div>
								</div>
							</div>
							<div v-if="uploadReady">
								<hr>
								<div class="card text-bg-success rounded-3">
									<div class="card-body">
										<i class="bi bi-person-fill me-2"></i>
										<LocaleText t="Contain"></LocaleText> <LocaleText t="Peer" v-if="peersCount > 1"></LocaleText><LocaleText t="Peer" v-else></LocaleText>
									</div>
								</div>
							</div>
						</div>
					</div>
					<div class="card-footer px-4 py-3">
						<div class="d-flex w-100">
							<button
								:disabled="!uploadReady"
								class="btn btn-dark btn-brand rounded-3 px-3 py-2 shadow ms-auto">
								<i class="bi bi-upload me-2"></i>
								Upload
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>
