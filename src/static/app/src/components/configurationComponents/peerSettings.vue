<script>
import {fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {GetLocale} from "@/utilities/locale.js";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "peerSettings",
	components: {LocaleText},
	props: {
		selectedPeer: Object
	},
	data(){
		return {
			data: undefined,
			dataChanged: false,
			showKey: false,
			saving: false,
			extendDays: 30,
			// "Безлимит": срок оплаты не задаётся, пир оплачен навсегда.
			// На бэкенде хранится дата-маркер 9999-12-31 в колонке paid_until
			paidUnlimited: false
		}
	},
	setup(){
		const dashboardConfigurationStore = DashboardConfigurationStore();
		return {dashboardConfigurationStore}
	},
	methods: {
		reset(){
			if (this.selectedPeer){
				this.data = JSON.parse(JSON.stringify(this.selectedPeer))
				this.paidUnlimited = this.data.PaidUntilFormatted === '9999-12-31';
				this.dataChanged = false;
			}
		},
		// При включении "Безлимит" очищаем дату: срок больше не задаётся,
		// а при выключении поле снова доступно для ввода
		toggleUnlimited(){
			if (this.paidUnlimited){
				this.data.PaidUntilFormatted = "";
			}
			this.dataChanged = true;
		},
		// Метод, а не computed: Vue вызывает computed-геттер без
		// аргументов, и параметры до localizeCount не доходят
		localizeCount(template, n){
			return GetLocale(template).replace('{n}', n);
		},
		// Продление идёт отдельным запросом: срок оплаты не относится к
		// VPN, поэтому обновление даты не должно дёргать awg и рвать
		// соединение клиента
		extendPayment(){
			if (!this.data || !this.extendDays) return;
			this.saving = true;
			fetchPost("/api/payments/extend", {
				Configuration: this.$route.params.id,
				Peer: this.data.id,
				Days: this.extendDays
			}, (res) => {
				this.saving = false;
				if (res.status){
					this.data.PaidUntilFormatted = res.data.PaidUntilFormatted;
					this.data.DaysRemaining = res.data.DaysRemaining;
					this.data.PaymentStatus = res.data.PaymentStatus;
					this.dashboardConfigurationStore.newMessage("Server", "Payment extended", "success");
					this.$emit("refresh");
				}else{
					this.dashboardConfigurationStore.newMessage("Server", res.message, "danger");
				}
			})
		},
		savePeer(){
			this.saving = true;
			/*
			 * Поле даты в форме связано с PaidUntilFormatted - это строка для
			 * показа ("2026-10-15"). Бэкенд же читает paid_until. Без этой
			 * подстановки отправлялся бы старый paid_until из объекта пира,
			 * и сохранение выглядело бы как "ничего не изменилось", хотя
			 * запрос уходит и отвечает успехом.
			 * "Безлимит" отправляет дату-маркер 9999-12-31: бэкенд хранит её
			 * в обычной колонке paid_until и всегда считает пир оплаченным.
			 */
			const payload = Object.assign({}, this.data, {
				paid_until: this.paidUnlimited ? '9999-12-31' : (this.data.PaidUntilFormatted || "")
			});
			fetchPost(`/api/updatePeerSettings/${this.$route.params.id}`, payload, (res) => {
				this.saving = false;
				if (res.status){
					// Присваиваем по полям, а не подменяем data: объект
					// взят из selectedPeer, который принадлежит родителю
					if (res.data){
						this.data.PaidUntilFormatted = res.data.PaidUntilFormatted;
						this.data.DaysRemaining = res.data.DaysRemaining;
						this.data.PaymentStatus = res.data.PaymentStatus;
						this.data.paid_until = res.data.paid_until;
						this.paidUnlimited = this.data.PaidUntilFormatted === '9999-12-31';
					}
					this.$emit("refresh")
					this.dashboardConfigurationStore.newMessage("Server", "Peer saved", "success")
				}else{
					this.dashboardConfigurationStore.newMessage("Server", res.message, "danger")
				}
			})
		},
		importSplitTunnelJSON(e){
			const file = e.target.files[0];
			// Сбрасываем значение input, чтобы повторный выбор того же файла сработал
			e.target.value = "";
			if (!file) return;
			const reader = new FileReader();
			reader.onload = (evt) => {
				try{
					const parsed = JSON.parse(evt.target.result);
					if (!Array.isArray(parsed)){
						throw new Error("Ожидался массив вида [{\"hostname\": \"10.0.0.0/8\", \"ip\": \"\"}]");
					}
					const extracted = [];
					const invalid = [];
					parsed.forEach(entry => {
						const value = (entry && (entry.hostname || entry.ip)) || "";
						if (typeof value === "string" && value.trim().length > 0){
							extracted.push(value.trim());
						}else{
							invalid.push(JSON.stringify(entry));
						}
					});
					if (extracted.length === 0){
						this.dashboardConfigurationStore.newMessage("WGDashboard", "В файле не найдено ни одного адреса", "danger");
						return;
					}
					this.data.split_tunnel_ips = extracted.join(", ");
					this.dataChanged = true;
					let msg = `Импортировано адресов: ${extracted.length}`;
					if (invalid.length > 0){
						msg += `. Пропущено некорректных записей: ${invalid.length}`;
					}
					this.dashboardConfigurationStore.newMessage("WGDashboard", msg, invalid.length > 0 ? "warning" : "success");
				}catch (e){
					this.dashboardConfigurationStore.newMessage("WGDashboard", `Не удалось прочитать файл: ${e.message}`, "danger");
				}
			};
			reader.onerror = () => {
				this.dashboardConfigurationStore.newMessage("WGDashboard", "Не удалось прочитать файл", "danger");
			};
			reader.readAsText(file);
		},
		resetPeerData(type){
			this.saving = true
			fetchPost(`/api/resetPeerData/${this.$route.params.id}`, {
				id: this.data.id,
				type: type
			}, (res) => {
				this.saving = false;
				if (res.status){
					this.dashboardConfigurationStore.newMessage("Server", "Peer data usage reset successfully", "success")
				}else{
					this.dashboardConfigurationStore.newMessage("Server", res.message, "danger")
				}
				this.$emit("refresh")
			})
		}
	},
	computed: {
		paymentBadge(){
			// "Безлимит" хранится как дата-маркер 9999-12-31 при статусе
			// active; показываем отдельный бейдж вместо даты окончания
			if (this.data?.PaidUntilFormatted === '9999-12-31'){
				return {icon: 'bi-infinity', text: 'Unlimited'}
			}
			switch (this.data?.PaymentStatus){
				case 'active':
					return {icon: 'bi-check-circle-fill', text: 'Paid'}
				case 'expiring':
					return {icon: 'bi-exclamation-triangle-fill', text: this.localizeCount('Expiring in {n} day(s)', this.data.DaysRemaining)}
				case 'expired':
					return {icon: 'bi-x-octagon-fill', text: this.localizeCount('Overdue by {n} day(s)', Math.abs(this.data.DaysRemaining))}
				default:
					return {icon: 'bi-dash-circle', text: 'No payment date set'}
			}
		}
	},
	beforeMount() {
		this.reset();
	},
	mounted() {
		this.$el.querySelectorAll("input").forEach(x => {
			x.addEventListener("change", () => {
				this.dataChanged = true;
			});
		})
	}
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal">
				<div class="card rounded-3 shadow flex-grow-1">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-2">
						<h4 class="mb-0">
							<LocaleText t="Peer Settings"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="this.$emit('close')"></button>
					</div>
					<div class="card-body px-4" v-if="this.data">
						<div class="d-flex flex-column gap-2 mb-4">
							<div class="d-flex align-items-center">
								<small class="text-muted">
									<LocaleText t="Public Key"></LocaleText>
								</small>
								<small class="ms-auto"><samp>{{this.data.id}}</samp></small>
							</div>
							<div>
								<label for="peer_name_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="Name"></LocaleText>
									</small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.name"
								       id="peer_name_textbox" placeholder="">
							</div>
							<div>
								<label for="peer_telegram_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="Telegram"></LocaleText>
									</small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.telegram"
								       id="peer_telegram_textbox" placeholder="@username">
							</div>
							<div class="row g-2">
								<div class="col-6">
									<label for="peer_paid_until" class="form-label">
										<small class="text-muted">
											<LocaleText t="Paid Until"></LocaleText>
										</small>
									</label>
									<input type="date" class="form-control form-control-sm rounded-3"
									       :disabled="this.saving || this.paidUnlimited"
									       v-model="this.data.PaidUntilFormatted"
									       id="peer_paid_until">
									<div class="form-check form-switch mt-2">
										<input class="form-check-input" type="checkbox" role="switch"
										       v-model="this.paidUnlimited"
										       :disabled="this.saving"
										       @change="this.toggleUnlimited()"
										       id="peer_paid_unlimited_switch">
										<label class="form-check-label" for="peer_paid_unlimited_switch">
											<small class="fw-bold">
												<LocaleText t="Unlimited"></LocaleText>
											</small>
										</label>
									</div>
								</div>
								<div class="col-6">
									<label for="peer_extend_days" class="form-label">
										<small class="text-muted">
											<LocaleText t="Extend by"></LocaleText>
										</small>
									</label>
									<div class="input-group input-group-sm">
										<input type="number" min="1" max="3650" class="form-control rounded-3"
										       :disabled="this.saving"
										       v-model.number="this.extendDays"
										       id="peer_extend_days">
										<button class="btn btn-outline-primary"
										        :disabled="this.saving || !this.extendDays"
										        @click="this.extendPayment()">
											<LocaleText t="Extend"></LocaleText>
										</button>
									</div>
								</div>
							</div>
							<div v-if="this.data.DaysRemaining !== null && this.data.DaysRemaining !== undefined">
								<div class="form-text d-flex align-items-center">
									<i class="bi me-1" :class="this.paymentBadge.icon"></i>
									{{this.paymentBadge.text}}
								</div>
							</div>
							<div>
								<label for="peer_payment_comment" class="form-label">
									<small class="text-muted">
										<LocaleText t="Comment"></LocaleText>
									</small>
								</label>
								<textarea class="form-control form-control-sm rounded-3" rows="2"
								          :disabled="this.saving"
								          v-model="this.data.payment_comment"
								          id="peer_payment_comment"
								          placeholder="Payment notes, method, anything for your own reference"></textarea>
							</div>
							<div class="form-text fst-italic">
								<LocaleText t="Payment status is only visible to the administrator. The client is never notified and access is not restricted."></LocaleText>
							</div>
							<div>
								<label for="peer_notes_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="Notes"></LocaleText>
									</small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.notes"
								       id="peer_notes_textbox" placeholder="">
							</div>
							<div>
								<div class="d-flex position-relative">
									<label for="peer_private_key_textbox" class="form-label">
										<small class="text-muted"><LocaleText t="Private Key"></LocaleText> 
											<code>
												<LocaleText t="(Required for QR Code and Download)"></LocaleText>
											</code></small>
									</label>
									<a role="button" class="ms-auto text-decoration-none toggleShowKey"
									   @click="this.showKey = !this.showKey"
									>
										<i class="bi" :class="[this.showKey ? 'bi-eye-slash-fill':'bi-eye-fill']"></i>
									</a>
								</div>
								<input :type="[this.showKey ? 'text':'password']" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.private_key"
								       id="peer_private_key_textbox"
								       style="padding-right: 40px">
							</div>
							<div>
								<label for="peer_allowed_ip_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="Allowed IPs"></LocaleText>
										<code>
											<LocaleText t="(Required)"></LocaleText>
										</code></small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.allowed_ip"
								       id="peer_allowed_ip_textbox">
							</div>

							<div>
								<label for="peer_endpoint_allowed_ips" class="form-label">
									<small class="text-muted">
										<LocaleText t="Endpoint Allowed IPs"></LocaleText>
										<code>
											<LocaleText t="(Required)"></LocaleText>
										</code></small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.endpoint_allowed_ip"
								       id="peer_endpoint_allowed_ips">
							</div>
							<div>
								<label for="peer_DNS_textbox" class="form-label">
									<small class="text-muted">
										<LocaleText t="DNS"></LocaleText>
									</small>
								</label>
								<input type="text" class="form-control form-control-sm rounded-3"
								       :disabled="this.saving"
								       v-model="this.data.DNS"
								       id="peer_DNS_textbox">
							</div>
							<div class="accordion my-3" id="peerSettingsAccordion">
								<div class="accordion-item">
									<h2 class="accordion-header">
										<button class="accordion-button rounded-3 collapsed" type="button"
										        data-bs-toggle="collapse" data-bs-target="#peerSettingsAccordionOptional">
											<LocaleText t="Optional Settings"></LocaleText>
										</button>
									</h2>
									<div id="peerSettingsAccordionOptional" class="accordion-collapse collapse"
									     data-bs-parent="#peerSettingsAccordion">
										<div class="accordion-body d-flex flex-column gap-2 mb-2">
											<div>
												<label for="peer_preshared_key_textbox" class="form-label">
													<small class="text-muted">
														<LocaleText t="Pre-Shared Key"></LocaleText></small>
												</label>
												<input type="text" class="form-control form-control-sm rounded-3"
												       :disabled="this.saving"
												       v-model="this.data.preshared_key"
												       id="peer_preshared_key_textbox">
											</div>
											<div>
												<label for="peer_mtu" class="form-label"><small class="text-muted">
													<LocaleText t="MTU"></LocaleText>
												</small></label>
												<input type="number" class="form-control form-control-sm rounded-3"
												       :disabled="this.saving"
												       v-model="this.data.mtu"
												       id="peer_mtu">
											</div>
											<div>
												<label for="peer_keep_alive" class="form-label">
													<small class="text-muted">
														<LocaleText t="Persistent Keepalive"></LocaleText>
													</small>
												</label>
												<input type="number" class="form-control form-control-sm rounded-3"
												       :disabled="this.saving"
												       v-model="this.data.keepalive"
												       id="peer_keep_alive">
											</div>
											<!-- Split Tunneling Settings -->
											<div>
												<label for="peer_split_tunnel_mode" class="form-label">
													<small class="text-muted">
														<LocaleText t="Split Tunnel Mode"></LocaleText>
													</small>
												</label>
												<select class="form-select form-select-sm rounded-3"
												        :disabled="this.saving"
												        v-model="this.data.split_tunnel_mode"
												        id="peer_split_tunnel_mode">
													<option value="include">Only these IPs through VPN</option>
													<option value="exclude">All except these IPs through VPN</option>
												</select>
											</div>
											<div>
												<label for="peer_split_tunnel_ips" class="form-label">
													<small class="text-muted">
														<LocaleText t="Split Tunnel IPs"></LocaleText>
													</small>
												</label>
												<textarea class="form-control form-control-sm rounded-3"
												          :disabled="this.saving"
												          v-model="this.data.split_tunnel_ips"
												          id="peer_split_tunnel_ips"
												          placeholder="e.g., 10.0.0.0/8, 172.16.0.0/12"
												          rows="3"></textarea>
												<div class="form-text d-flex align-items-center gap-2">
												<span>IP-адреса/CIDR для раздельного туннелирования (через запятую или по одному на строку)</span>
												<button type="button" class="btn btn-sm btn-outline-primary ms-auto"
												        @click="this.$refs.splitTunnelFile.click()">
													<i class="bi bi-upload me-1"></i>
													<LocaleText t="Import from JSON"></LocaleText>
												</button>
												<input type="file" class="d-none" accept=".json,application/json"
												       ref="splitTunnelFile" @change="this.importSplitTunnelJSON">
											</div>
											</div>
										</div>
									</div>
								</div>
							</div>
							<div class="d-flex align-items-center gap-2">
								<button class="btn bg-secondary-subtle border-secondary-subtle text-secondary-emphasis rounded-3 shadow ms-auto px-3 py-2"
								        @click="this.reset()"
								        :disabled="!this.dataChanged || this.saving">
									<i class="bi bi-arrow-clockwise me-2"></i>
									<LocaleText t="Reset"></LocaleText>
								</button>

								<button class="btn bg-primary-subtle border-primary-subtle text-primary-emphasis rounded-3 px-3 py-2 shadow"
								        :disabled="!this.dataChanged || this.saving"
								        @click="this.savePeer()"
								>
									<i class="bi bi-save-fill me-2"></i>
									<LocaleText t="Save"></LocaleText>
								</button>
							</div>
							<hr>
							<div class="d-flex gap-2 align-items-center">
								<strong>
									<LocaleText t="Reset Data Usage"></LocaleText>
								</strong>
								<div class="d-flex gap-2 ms-auto">
									<button class="btn bg-primary-subtle text-primary-emphasis rounded-3 flex-grow-1 shadow-sm"
										@click="this.resetPeerData('total')"
									>
										<i class="bi bi-arrow-down-up me-2"></i>
										<LocaleText t="Total"></LocaleText>
									</button>
									<button class="btn bg-primary-subtle text-primary-emphasis rounded-3 flex-grow-1 shadow-sm"
									        @click="this.resetPeerData('receive')"
									>
										<i class="bi bi-arrow-down me-2"></i>
										<LocaleText t="Received"></LocaleText>
									</button>
									<button class="btn bg-primary-subtle text-primary-emphasis rounded-3  flex-grow-1 shadow-sm"
									        @click="this.resetPeerData('sent')"
									>
										<i class="bi bi-arrow-up me-2"></i>
										<LocaleText t="Sent"></LocaleText>
									</button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
			
		</div>

	</div>
</template>

<style scoped>
.toggleShowKey{
	position: absolute;
	top: 35px;
	right: 12px;
}
</style>