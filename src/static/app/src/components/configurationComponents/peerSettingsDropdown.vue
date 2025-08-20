<script>
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import LocaleText from "@/components/text/localeText.vue";
import PeerSettingsDropdownTool
	from "@/components/configurationComponents/peerSettingsDropdownComponents/peerSettingsDropdownTool.vue";
import PeerTagSelectDropdown
	from "@/components/configurationComponents/peerSettingsDropdownComponents/peerTagSelectDropdown.vue";
import {onMounted} from "vue";

export default {
	name: "peerSettingsDropdown",
	components: {PeerTagSelectDropdown, PeerSettingsDropdownTool, LocaleText},
	setup(){
		const dashboardStore = DashboardConfigurationStore()
		return {dashboardStore}
	},
	props: {
		Peer: Object, ConfigurationInfo: Object, dropup: Boolean
	},
	data(){
		return{
			deleteBtnDisabled: false,
			restrictBtnDisabled: false,
			allowAccessBtnDisabled: false,
			confirmDelete: false,
			height: 0
		}
	},
	mounted() {
		this.height = document.querySelector("#peerDropdown").clientHeight
	},
	methods: {
		downloadPeer(){
			fetchGet("/api/downloadPeer/"+this.$route.params.id, {
				id: this.Peer.id
			}, (res) => {
				if (res.status){
					const blob = new Blob([res.data.file], { type: "text/plain" });
					const jsonObjectUrl = URL.createObjectURL(blob);
					const filename = `${res.data.fileName}.conf`;
					const anchorEl = document.createElement("a");
					anchorEl.href = jsonObjectUrl;
					anchorEl.download = filename;
					anchorEl.click();
					this.dashboardStore.newMessage("WGDashboard", "Peer download started", "success")
				}else{
					this.dashboardStore.newMessage("Server", res.message, "danger")
				}
			})
		},
		downloadQRCode(emit){
			fetchGet("/api/downloadPeer/"+this.$route.params.id, {
				id: this.Peer.id
			}, (res) => {
				if (res.status){
					this.$emit(emit, res.data.file)					
				}else{
					this.dashboardStore.newMessage("Server", res.message, "danger")
				}
			})
		},
		deletePeer(){
			this.deleteBtnDisabled = true
			fetchPost(`/api/deletePeers/${this.$route.params.id}`, {
				peers: [this.Peer.id]
			}, (res) => {
				this.dashboardStore.newMessage("Server", res.message, res.status ? "success":"danger")
				this.$emit("refresh")
				this.deleteBtnDisabled = false
			})
		},
		restrictPeer(){
			this.restrictBtnDisabled = true
			fetchPost(`/api/restrictPeers/${this.$route.params.id}`, {
				peers: [this.Peer.id]
			}, (res) => {
				this.dashboardStore.newMessage("Server", res.message, res.status ? "success":"danger")
				this.$emit("refresh")
				this.restrictBtnDisabled = false
			})
		},
		allowAccessPeer(){
			this.allowAccessBtnDisabled = true
			fetchPost(`/api/allowAccessPeers/${this.$route.params.id}`, {
				peers: [this.Peer.id]
			}, (res) => {
				this.dashboardStore.newMessage("Server", res.message, res.status ? "success":"danger")
				this.$emit("refresh")
				this.allowAccessBtnDisabled = false
			})
		},

	}
}
</script>

<template>
	<ul
		:class="{'dropup': dropup}"
		class="dropdown-menu mt-2 shadow-lg d-block rounded-3" id="peerDropdown" style="max-width: 200px">
		<template v-if="!this.Peer.restricted">
			<template v-if="!this.confirmDelete">
				<template v-if="this.Peer.status === 'running'">
					<li style="font-size: 0.8rem; padding-left: var(--bs-dropdown-item-padding-x); padding-right: var(--bs-dropdown-item-padding-x);">
						<span class="text-body d-flex">
								<i class="bi bi-box-arrow-in-right"></i>
								<span class="ms-auto">
									{{this.Peer.endpoint}}
								</span>
						</span>
					</li>
					<li><hr class="dropdown-divider"></li>
				</template>
				<template v-if="!this.Peer.private_key">
					<li>
						<small class="w-100 dropdown-item text-muted"
						       style="white-space: break-spaces; font-size: 0.7rem">
							<LocaleText t="Download & QR Code is not available due to no private key set for this peer"></LocaleText>
						</small>
					</li>
				</template>
				<template v-else>
					<li>
						<div class="text-center text-muted">
							
						</div>
						<div class="d-flex" style="padding-left: var(--bs-dropdown-item-padding-x); padding-right: var(--bs-dropdown-item-padding-x);">
							<PeerSettingsDropdownTool icon="bi-download" 
							                          title="Download"
							                          @click="this.downloadPeer()"></PeerSettingsDropdownTool>
							<PeerSettingsDropdownTool icon="bi-qr-code" 
							                          title="QR Code"
							                          @click="this.$emit('qrcode')"></PeerSettingsDropdownTool>
							<PeerSettingsDropdownTool icon="bi-body-text" 
							                          title="Configuration File"
							                          @click="this.$emit('configurationFile')"></PeerSettingsDropdownTool>
							<PeerSettingsDropdownTool icon="bi-share" 
							                          title="Share Peer"
							                          @click="this.$emit('share')"></PeerSettingsDropdownTool>
						</div>
					</li>
				</template>
				<li><hr class="dropdown-divider"></li>
				<li>
					<a class="dropdown-item d-flex" role="button"
					   @click="this.$emit('setting')"
					>
						<i class="me-auto bi bi-pen"></i> <LocaleText t="Peer Settings"></LocaleText>
					</a>
				</li>
				<li>
					<a class="dropdown-item d-flex" role="button"
					   @click="this.$emit('jobs')"
					>
						<i class="me-auto bi bi-app-indicator"></i> <LocaleText t="Schedule Jobs"></LocaleText>
					</a>
				</li>
				<li>
					<a class="dropdown-item d-flex" role="button"
					   @click="this.$emit('assign')"
					>
						<i class="me-auto bi bi-diagram-2"></i> <LocaleText t="Assign Peer"></LocaleText>
					</a>
				</li>
				<li class="dropdown dropstart">
					<a class="dropdown-item d-flex " role="button"
					   data-bs-auto-close="outside"
					   data-bs-toggle="dropdown"

					>
						<i class="me-auto bi bi-tag"></i> <LocaleText t="Tag Peer"></LocaleText>
					</a>
					<PeerTagSelectDropdown
						@update="this.$emit('refresh')"
						:Peer="Peer" :ConfigurationInfo="ConfigurationInfo"></PeerTagSelectDropdown>
				</li>
				<li><hr class="dropdown-divider"></li>
				<li>
					<a class="dropdown-item d-flex text-warning"
					   @click="this.restrictPeer()"
					   :class="{disabled: this.restrictBtnDisabled}"
					   role="button">
						<i class="me-auto bi bi-lock"></i>
						<LocaleText t="Restrict Access" v-if="!this.restrictBtnDisabled"></LocaleText>
						<LocaleText t="Restricting..." v-else></LocaleText>

					</a>
				</li>
				<li>
					<a class="dropdown-item d-flex fw-bold text-danger"
					   @click="this.confirmDelete = true"
					   :class="{disabled: this.deleteBtnDisabled}"
					   role="button">
						<i class="me-auto bi bi-trash"></i>
						<LocaleText t="Delete" v-if="!this.deleteBtnDisabled"></LocaleText>
						<LocaleText t="Deleting..." v-else></LocaleText>
					</a>
				</li>
			</template>
			<template v-else>
				<li class="confirmDelete">
					<p style="white-space: break-spaces" class="mb-2 d-block fw-bold">
						<LocaleText t="Are you sure to delete this peer?"></LocaleText>
					</p>
					<div class="d-flex w-100 gap-2">
						<button
							@click="this.deletePeer()"
							:disabled="this.deleteBtnDisabled"
							class="flex-grow-1 ms-auto btn btn-sm bg-danger">
							<LocaleText t="Yes"></LocaleText>
						</button>
						<button
							:disabled="this.deleteBtnDisabled"
							@click="this.confirmDelete = false"
							class="flex-grow-1 btn btn-sm bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle">
							<LocaleText t="No"></LocaleText>
						</button>
						
					</div>
				</li>
			</template>
		</template>
		<template v-else>
			<li>
				<a class="dropdown-item d-flex text-warning"

				   @click="this.allowAccessPeer()"
				   :class="{disabled: this.allowAccessBtnDisabled}"
				   role="button">
					<i class="me-auto bi bi-unlock"></i>
					<LocaleText t="Allow Access" v-if="!this.allowAccessBtnDisabled"></LocaleText>
					<LocaleText t="Allowing Access..." v-else></LocaleText>
				</a>
			</li>
		</template>
	</ul>
</template>

<style scoped>
.dropdown-menu{
	right: 0;
	min-width: 200px;
}

.dropdown-menu.dropup{
	bottom: 100%;
}

.dropdown-item.disabled, .dropdown-item:disabled{
	opacity: 0.7;
}

.confirmDelete{
	padding: var(--bs-dropdown-item-padding-y) var(--bs-dropdown-item-padding-x);
}
</style>