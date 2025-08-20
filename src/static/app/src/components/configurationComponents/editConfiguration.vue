<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {reactive, ref, watch} from "vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import UpdateConfigurationName
	from "@/components/configurationComponents/editConfigurationComponents/updateConfigurationName.vue";
import EditRawConfigurationFile
	from "@/components/configurationComponents/editConfigurationComponents/editRawConfigurationFile.vue";
import DeleteConfiguration from "@/components/configurationComponents/deleteConfiguration.vue";
import ConfigurationBackupRestore from "@/components/configurationComponents/configurationBackupRestore.vue";
import EditPeerSettingsOverride
	from "@/components/configurationComponents/editConfigurationComponents/editPeerSettingsOverride.vue";
const props = defineProps({
	configurationInfo: Object
})
const wgStore = WireguardConfigurationsStore()
const store = DashboardConfigurationStore()
const saving = ref(false)
const data = reactive(JSON.parse(JSON.stringify(props.configurationInfo)))
const editPrivateKey = ref(false)
const dataChanged = ref(false)
const reqField = reactive({
	PrivateKey: true,
	IPAddress: true,
	ListenPort: true
})
const genKey = () => {
	if (wgStore.checkWGKeyLength(data.PrivateKey)){
		reqField.PrivateKey = true;
		data.PublicKey = window.wireguard.generatePublicKey(data.PrivateKey)
	}else{
		reqField.PrivateKey = false;
	}
}
const resetForm = () => {
	dataChanged.value = false;
	Object.assign(data, JSON.parse(JSON.stringify(props.configurationInfo)))
}
const emit = defineEmits(["changed", "close", "refresh", "dataChanged"])
const saveForm = ()  => {
	saving.value = true
	fetchPost("/api/updateWireguardConfiguration", data, (res) => {
		saving.value = false
		if (res.status){
			store.newMessage("Server", "Configuration saved", "success")
			dataChanged.value = false
			emit("dataChanged", res.data)
			
		}else{
			store.newMessage("Server", res.message, "danger")
		}
	})
}
const updateConfigurationName = ref(false)

watch(data, () => {
	dataChanged.value = JSON.stringify(data) !== JSON.stringify(props.configurationInfo);
}, {
	deep: true
})

const editRawConfigurationFileModal = ref(false)
const backupRestoreModal = ref(false)
const deleteConfigurationModal = ref(false)


</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0" ref="editConfigurationContainer">
		<div class="w-100 h-100  overflow-y-scroll">
			<TransitionGroup name="zoom">
				<EditRawConfigurationFile
					name="EditRawConfigurationFile"
					v-if="editRawConfigurationFileModal"
					@close="editRawConfigurationFileModal = false">
				</EditRawConfigurationFile>
				<DeleteConfiguration
					key="DeleteConfiguration"
					@backup="backupRestoreModal = true"
					@close="deleteConfigurationModal = false"
					v-if="deleteConfigurationModal">
				</DeleteConfiguration>
				<ConfigurationBackupRestore
					@close="backupRestoreModal = false"
					@refreshPeersList="emit('refresh')"
					v-if="backupRestoreModal">
				</ConfigurationBackupRestore>
			</TransitionGroup>

			<div class="container d-flex h-100 w-100">
				<div class="m-auto modal-dialog-centered dashboardModal" style="width: 700px">
					<div class="card rounded-3 shadow flex-grow-1">
						<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4">
							<h4 class="mb-0">
								<LocaleText t="Configuration Settings"></LocaleText>
							</h4>
							<button type="button" class="btn-close ms-auto" @click="$emit('close')"></button>
						</div>
						<div class="card-body px-4 pb-4">
							<div class="d-flex gap-2 flex-column">
								<div class="d-flex align-items-center gap-3" v-if="!updateConfigurationName">
									<small class="text-muted">
										<LocaleText t="Name"></LocaleText>
									</small>
									<small>{{data.Name}}</small>
									<button
										@click="updateConfigurationName = true"
										class="btn btn-sm bg-danger-subtle border-danger-subtle text-danger-emphasis rounded-3 ms-auto">
										<LocaleText t="Update Name"></LocaleText>
									</button>
								</div>
								<UpdateConfigurationName
									@close="updateConfigurationName = false"
									:configuration-name="data.Name"
									v-if="updateConfigurationName"></UpdateConfigurationName>
								<template v-else>
									<hr>
									<div class="d-flex align-items-center gap-3">
										<small class="text-muted" style="word-break: keep-all">
											<LocaleText t="Public Key"></LocaleText>
										</small>
										<small class="ms-auto"  style="word-break: break-all">
											{{data.PublicKey}}
										</small>
									</div>
									<hr>
									<div>
										<div class="d-flex">
											<label for="configuration_private_key" class="form-label">
												<small class="text-muted d-block">
													<LocaleText t="Private Key"></LocaleText>
												</small>
											</label>
											<div class="form-check form-switch ms-auto">
												<input class="form-check-input"
												       type="checkbox" role="switch" id="editPrivateKeySwitch"
												       v-model="editPrivateKey"
												>
												<label class="form-check-label" for="editPrivateKeySwitch">
													<small>Edit</small>
												</label>
											</div>
										</div>
										<input type="text" class="form-control form-control-sm rounded-3"
										       :disabled="saving || !editPrivateKey"
										       :class="{'is-invalid': !reqField.PrivateKey}"
										       @keyup="genKey()"
										       v-model="data.PrivateKey"
										       id="configuration_private_key">
									</div>
									<div>
										<label for="configuration_ipaddress_cidr" class="form-label">
											<small class="text-muted">
												<LocaleText t="IP Address/CIDR"></LocaleText>
											</small>
										</label>
										<input type="text" class="form-control form-control-sm rounded-3"
										       :disabled="saving"
										       v-model="data.Address"
										       id="configuration_ipaddress_cidr">
									</div>
									<div>
										<label for="configuration_listen_port" class="form-label">
											<small class="text-muted">
												<LocaleText t="Listen Port"></LocaleText>
											</small>
										</label>
										<input type="number" class="form-control form-control-sm rounded-3"
										       :disabled="saving"
										       v-model="data.ListenPort"
										       id="configuration_listen_port">

									</div>
									<div class="accordion mt-2" id="editConfigurationOptionalAccordion">
										<div class="accordion-item">
											<h2 class="accordion-header">
												<button class="accordion-button collapsed px-3 py-2" type="button" data-bs-toggle="collapse" data-bs-target="#editOptionalAccordionCollapse">
													<small class="text-muted">
														<LocaleText t="Optional Settings"></LocaleText>
													</small>
												</button>
											</h2>
											<div id="editOptionalAccordionCollapse"
											     class="accordion-collapse collapse" data-bs-parent="#editConfigurationOptionalAccordion">
												<div class="accordion-body d-flex flex-column gap-3">
													<div v-for="key in ['Table', 'PreUp', 'PreDown', 'PostUp', 'PostDown']">
														<label :for="'configuration_' + key" class="form-label">
															<small class="text-muted">
																<LocaleText :t="key"></LocaleText>
															</small>
														</label>
														<input type="text" class="form-control form-control-sm rounded-3"
														       :disabled="saving"
														       v-model="data[key]"
														       :id="'configuration_' + key">
													</div>
													<div v-for="key in ['Jc', 'Jmin', 'Jmax', 'S1', 'S2', 'H1', 'H2', 'H3', 'H4']"
													     v-if="configurationInfo.Protocol === 'awg'">
														<label :for="'configuration_' + key" class="form-label">
															<small class="text-muted">
																<LocaleText :t="key"></LocaleText>
															</small>
														</label>
														<input type="number" class="form-control form-control-sm rounded-3"
														       :disabled="saving"
														       v-model="data[key]"
														       :id="'configuration_' + key">
													</div>
												</div>
											</div>
										</div>
									</div>
									<div class="d-flex align-items-center gap-2 mt-1">
										<button class="btn btn-sm bg-secondary-subtle border-secondary-subtle text-secondary-emphasis rounded-3 shadow ms-auto"
										        @click="resetForm()"
										        :disabled="!dataChanged || saving">
											<i class="bi bi-arrow-clockwise me-2"></i>
											<LocaleText t="Reset"></LocaleText>
										</button>
										<button class="btn btn-sm bg-primary-subtle border-primary-subtle text-primary-emphasis rounded-3 shadow"
										        :disabled="!dataChanged || saving"
										        @click="saveForm()"
										>
											<i class="bi bi-save-fill me-2"></i>
											<LocaleText t="Save"></LocaleText>
										</button>
									</div>
									<hr>
									<EditPeerSettingsOverride :configuration="configurationInfo"></EditPeerSettingsOverride>
									<hr>
									<h5 class="mb-3">
										<LocaleText t="Danger Zone"></LocaleText>
									</h5>
									<div class="d-flex gap-2 flex-column">
										<button
											@click="backupRestoreModal = true"
											class="btn bg-warning-subtle border-warning-subtle text-warning-emphasis rounded-3 text-start d-flex">
											<i class="bi bi-copy me-auto"></i>
											<LocaleText t="Backup & Restore"></LocaleText>
										</button>
										<button
											@click="editRawConfigurationFileModal = true"
											class="btn bg-warning-subtle border-warning-subtle text-warning-emphasis rounded-3 d-flex">
											<i class="bi bi-pen me-auto"></i>
											<LocaleText t="Edit Raw Configuration File"></LocaleText>
										</button>

										<button
											@click="deleteConfigurationModal = true"
											class="btn bg-danger-subtle border-danger-subtle text-danger-emphasis rounded-3 d-flex mt-4">
											<i class="bi bi-trash-fill me-auto"></i>
											<LocaleText t="Delete Configuration"></LocaleText>
										</button>
									</div>
								</template>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>