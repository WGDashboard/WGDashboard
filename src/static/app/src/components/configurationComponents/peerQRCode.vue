<script>
import QRCode from "qrcode";
import LocaleText from "@/components/text/localeText.vue";
import {fetchGet} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
export default {
	name: "peerQRCode",
	components: {LocaleText},
	props: {
		selectedPeer: Object
	},
	setup(){
		const dashboardStore = DashboardConfigurationStore();
		return {dashboardStore}
	},
	data(){
		return{
			loading: true
		}
	},
	mounted() {
		fetchGet("/api/downloadPeer/"+this.$route.params.id, {
			id: this.selectedPeer.id
		}, (res) => {
			this.loading = false;
			if (res.status){
				let data = ""
				if (this.selectedPeer.configuration.Protocol === "awg"){
					let awgQRCodeObject = {
						containers: [
							{
								awg: {
									isThirdPartyConfig: true,
									last_config: res.data.file,
									port: this.selectedPeer.configuration.ListenPort,
									transport_proto: "udp"
								},
								container: "amnezia-awg",
							}
						],
						defaultContainer: "amnezia-awg",
						description: this.selectedPeer.name,
						hostName: this.dashboardStore.Configuration.Peers.remote_endpoint
					}
					QRCode.toCanvas(
						document.querySelector("#awg_vpn_qrcode"), btoa(JSON.stringify(awgQRCodeObject)), (error) => {
							if (error) console.error(error)
						}
					)
				}
				data = res.data.file
				QRCode.toCanvas(document.querySelector("#qrcode"), data,  (error) => {
					if (error) console.error(error)
				})
			}else{
				this.dashboardStore.newMessage("Server", res.message, "danger")
			}
		})
	}
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal justify-content-center">
				<div class="card rounded-3 shadow">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-0">
						<h4 class="mb-0">
							<LocaleText t="QR Code"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="this.$emit('close')" aria-label="Close"></button>
					</div>
					<div class="card-body p-4">
						<div class="d-flex gap-2 flex-column">
							<div class="d-flex flex-column gap-2 align-items-center">
								<canvas id="qrcode"
										style="width: 200px !important; height: 200px !important;"
										class="rounded-3 shadow animate__animated animate__fadeIn animate__faster qrcode"
										:class="{'d-none': loading}"></canvas>
								<LocaleText t="Scan with WireGuard App" class="text-muted" v-if='this.selectedPeer.configuration.Protocol === "wg"'></LocaleText>
								<LocaleText t="Scan with AmneziaWG App" class="text-muted" v-if='this.selectedPeer.configuration.Protocol === "awg"'></LocaleText>
							</div>
							<div v-if='this.selectedPeer.configuration.Protocol === "awg"' class="d-flex flex-column gap-2 align-items-center">
								<canvas id="awg_vpn_qrcode" class="rounded-3 shadow animate__animated animate__fadeIn animate__faster  qrcode"
										:class="{'d-none': loading}"></canvas>
								<LocaleText t="Scan with AmneziaVPN App" class="text-muted"></LocaleText>
							</div>
							<div class="spinner-border m-auto" role="status" v-if="loading">
								<span class="visually-hidden">Loading...</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
@media screen and (max-width: 768px) {
	.qrcode{
		width: 100% !important;
		height: auto !important;
		aspect-ratio: 1/1;
	}
}

.qrcode{
	width: 200px !important;
	height: 200px !important;
}
</style>