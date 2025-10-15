<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {useRoute, useRouter} from "vue-router";
import {onMounted, ref, useTemplateRef} from "vue";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
const route = useRoute()
const configurationName = route.params.id;
const input = ref("")
const router = useRouter()
const store = DashboardConfigurationStore()
const deleting = ref(false)

const deleteConfiguration = () => {
	clearInterval(store.Peers.RefreshInterval)
	deleting.value = true;
	fetchPost("/api/deleteWireguardConfiguration", {
		ConfigurationName: configurationName
	}, (res) => {
		if (res.status){
			router.push('/')
			store.newMessage("Server", "Configuration deleted", "success")
		}else{
			deleting.value = false;
		}
	})
}


const loading = ref(true)
const backups = ref([])
const getBackup = () => {
	loading.value = true;
	fetchGet("/api/getWireguardConfigurationBackup", {
		configurationName: configurationName
	}, (res) => {
		backups.value = res.data;
		loading.value = false;
	})
}
onMounted(() => {
	getBackup()
})
const emits = defineEmits(["backup", "close"])
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal" style="width: 700px">
				<div class="card rounded-3 shadow flex-grow-1 bg-danger-subtle border-danger-subtle" id="deleteConfigurationContainer">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-0">
						<h5 class="mb-0">
							<LocaleText t="Are you sure to delete this configuration?"></LocaleText>
						</h5>
						<button type="button" class="btn-close ms-auto" @click="emits('close')"></button>
					</div>
					<div class="card-body px-4 text-muted">
						<p class="mb-0">
							<LocaleText t="Once you deleted this configuration:"></LocaleText>
						</p>
						<ul>
							<li>
								<LocaleText t="All connected peers will get disconnected"></LocaleText>
							</li>
							<li>
								<LocaleText t="Both configuration file (.conf) and database table related to this configuration will get deleted"></LocaleText>
							</li>
						</ul>
						 
						<div class="alert"
						     :class="[loading ? 'alert-secondary' : (backups.length > 0 ? 'alert-success' : 'alert-danger')]">
							<div v-if="loading">
								<i class="bi bi-search me-2"></i>
								<LocaleText t="Checking backups..."></LocaleText>
							</div>
							<div v-else-if="backups.length > 0">
								<i class="bi bi-check-circle-fill me-2"></i>
								<LocaleText :t="'This configuration has ' + backups.length + ' backups'"></LocaleText>
							</div>
							<div v-else class="d-flex align-items-center gap-2">
								<i class="bi bi-x-circle-fill me-2"></i>
								<LocaleText t="This configuration has no backup"></LocaleText>
								<a role="button" 
								   @click="emits('backup')"
								   class="ms-auto btn btn-sm btn-primary rounded-3">
									<i class="bi bi-clock-history me-2"></i>
									<LocaleText t="Backup"></LocaleText>
								</a>
								<a role="button"
								   @click="getBackup()"
								   class="btn btn-sm btn-primary rounded-3">
									<i class="bi bi-arrow-clockwise"></i>
								</a>
							</div>
						</div>
						<hr>
						<p>
							<LocaleText t="If you're sure, please type in the configuration name below and click Delete"></LocaleText>
						</p>
						<input class="form-control rounded-3 mb-3" 
						       :placeholder="configurationName"
						       v-model="input"
						       type="text">
						<button class="btn btn-danger w-100" 
						        @click="deleteConfiguration()"
						        :disabled="input !== configurationName || deleting">
							<i class="bi bi-trash-fill me-2 rounded-3"></i>
							<LocaleText t="Delete" v-if="!deleting"></LocaleText>
							<LocaleText t="Deleting..." v-else></LocaleText>
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>
