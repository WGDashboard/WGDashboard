<script setup>
import LocaleText from "@/components/text/localeText.vue";
import CodeEditor from "@/utilities/simple-code-editor/CodeEditor.vue";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {useRoute} from "vue-router";
import {computed, onMounted, ref} from "vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {initSystemThemeWatcher, resolveTheme} from "@/utilities/theme.js";
const emits = defineEmits(['close'])
const route = useRoute()

const content = ref("")
const path = ref("")
const error = ref(false)
const errorMessage = ref("")

const getRaw = async () => {
	await fetchGet('/api/getWireguardConfigurationRawFile', {
		configurationName: route.params.id
	}, (res) => {
		content.value = res.data.content
		path.value = res.data.path
	})
}

await getRaw()
const dashboardStore = DashboardConfigurationStore();
const saving = ref(false)
const editorTheme = computed(() => {
	return resolveTheme(dashboardStore.Configuration.Server.dashboard_theme) === "dark" ? "github-dark" : "github";
});

onMounted(() => {
	initSystemThemeWatcher();
});

const saveRaw = async () => {
	saving.value = true
	await fetchPost('/api/updateWireguardConfigurationRawFile', {
		configurationName: route.params.id,
		rawConfiguration: content.value
	}, (res) => {
		if (res.status){
			error.value = false
			dashboardStore.newMessage("Server", "Configuration saved", "success")
		}else{
			error.value = true
			errorMessage.value = res.message
		}
		saving.value = false
	})
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal" style="width: 1000px">
				<div class="card rounded-3 shadow flex-grow-1" id="deleteConfigurationContainer">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-0">
						<h5 class="mb-0">
							<LocaleText t="Edit Raw Configuration File"></LocaleText>
						</h5>
						<button type="button" class="btn-close ms-auto" @click="emits('close')"></button>
					</div>
					<div class="card-body px-4 d-flex flex-column gap-3">
						<div class="alert alert-danger rounded-3 mb-0" v-if="error">
							<div class="mb-2">
								<strong>
									<LocaleText t="Failed to save configuration. Please see the following error message:"></LocaleText>
								</strong>
							</div>
							<div class="bg-body w-100 p-2 rounded-3">
								<pre>{{errorMessage}}</pre>
							</div>
						</div>
						<CodeEditor
							:disabled="true"
							:read-only="saving"
							v-model="content"
							:theme="editorTheme"
							:languages="[['ini', path]]"
							width="100%" height="600px">
						</CodeEditor>
						<div class="d-flex gap-2">
							<button class="btn bg-secondary-subtle border-secondary-subtle text-secondary-emphasis rounded-3 shadow ms-auto px-3 py-2"
							        :disabled="saving"
							        @click="getRaw()">
								<i class="bi bi-arrow-clockwise me-2"></i>
								<LocaleText t="Reset"></LocaleText>
							</button>
							<button 
								@click="saveRaw()"
								:disabled="saving"
								class="btn bg-danger-subtle border-danger-subtle text-danger-emphasis rounded-3 px-3 py-2 shadow"
							>
								<i class="bi bi-save-fill me-2"></i>
								<LocaleText t="Save" v-if="!saving"></LocaleText>
								<LocaleText t="Saving..." v-else></LocaleText>
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
