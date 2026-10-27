<script>
import { ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import "animate.css"
import PeerSettingsDropdown from "@/components/configurationComponents/peerSettingsDropdown.vue";
import LocaleText from "@/components/text/localeText.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {GetLocale} from "@/utilities/locale.js";
import {fetchPost} from "@/utilities/fetch.js";
import PeerTagBadge from "@/components/configurationComponents/peerTagBadge.vue";

export default {
	name: "peer",
	methods: {
		GetLocale,
		/**
		 * Подстановка числа в переводимую строку вида "Overdue by {n} day(s)".
		 *
		 * Именно метод, а не computed: computed вызывается Vue без
		 * аргументов, поэтому параметры до него не доходят.
		 */
		localizeCount(template, n){
			return GetLocale(template).replace('{n}', n)
		},
		/**
		 * Продление срока прямо из карточки пира.
		 *
		 * Отдельный запрос, а не сохранение настроек: срок оплаты не
		 * относится к VPN, поэтому обновление не должно дёргать awg и
		 * рвать соединение клиента. Ответом обновляем отдельные поля, а
		 * не подменяем объект Peer - он является источником данных для
		 * родительского списка, и подмена ломала бы реактивность.
		 */
		extendPayment(){
			if (!this.extendDays) return;
			fetchPost("/api/payments/extend", {
				Configuration: this.$route.params.id,
				Peer: this.Peer.id,
				Days: this.extendDays
			}, (res) => {
				if (res.status){
					this.Peer.PaidUntilFormatted = res.data.PaidUntilFormatted;
					this.Peer.DaysRemaining = res.data.DaysRemaining;
					this.Peer.PaymentStatus = res.data.PaymentStatus;
					this.Peer.paid_until = res.data.paid_until;
					this.$emit("refresh");
				}else{
					this.dashboardStore.newMessage("WGDashboard", res.message, "danger");
				}
			})
		}
	},
	components: {
		PeerTagBadge, LocaleText, PeerSettingsDropdown
	},
	props: {
		Peer: Object, ConfigurationInfo: Object, order: Number, searchPeersLength: Number
	},
	data(){
		return {
			extendDays: 30
		}
	},
	setup(){
		const target = ref(null);
		const subMenuOpened = ref(false)
		const dashboardStore = DashboardConfigurationStore()
		onClickOutside(target, event => {
			subMenuOpened.value = false;
		});
		return {target, subMenuOpened, dashboardStore}
	},
	computed: {
		getLatestHandshake(){
			if (this.Peer.latest_handshake.includes(",")){
				return this.Peer.latest_handshake.split(",")[0]
			}
			return this.Peer.latest_handshake;
		},
		getDropup(){
			return this.searchPeersLength - this.order <= 3
		},
		paymentBadge(){
			// "Безлимит": срок - дата-маркер 9999-12-31 при статусе active,
			// поэтому проверяем её раньше общего свитча по статусу
			if (this.Peer.PaidUntilFormatted === '9999-12-31'){
				return {cls: 'text-bg-success', icon: 'bi-infinity', text: GetLocale('Unlimited')}
			}
			switch (this.Peer.PaymentStatus){
				case 'active':
					return {cls: 'text-bg-success', icon: 'bi-check-circle-fill', text: GetLocale('Paid')}
				case 'expiring':
					return {cls: 'text-bg-warning', icon: 'bi-exclamation-triangle-fill', text: GetLocale('Expiring soon')}
				case 'expired':
					return {cls: 'text-bg-danger', icon: 'bi-x-octagon-fill', text: GetLocale('Payment overdue')}
				default:
					return {cls: 'text-bg-secondary', icon: 'bi-dash-circle', text: GetLocale('No payment date set')}
			}
		},
		// Подсказка с точным числом дней: в бейдже умещается только
		// общий статус, поэтому конкретика уходит в title
		paymentTitle(){
			if (this.Peer.PaidUntilFormatted === '9999-12-31') return GetLocale('Unlimited')
			const days = this.Peer.DaysRemaining
			if (days === null || days === undefined) return GetLocale('No payment date set')
			if (days < 0) return this.localizeCount('Overdue by {n} day(s)', Math.abs(days))
			return this.localizeCount('{n} day(s) left', days)
		},
		// Подсветка всей карточки. Цвет границы задаётся здесь, фон - в CSS
		// переменных, потому что у Bootstrap 5.3 нет готового цвета фона
		// для warning/danger, есть только варианты text-bg-*
		cardPaymentClass(){
			switch (this.Peer.PaymentStatus){
				case 'expired':
					return 'peer-card-overdue'
				case 'expiring':
					return 'peer-card-expiring'
				default:
					return ''
			}
		},
		// Дата в формате 15.10.2026: ISO-строку из БД не нужно
		// преобразовывать через Date, иначе время сдвигается по часовому
		// поясу браузера и дата может "уехать" на день назад
		paymentDate(){
			const value = this.Peer.PaidUntilFormatted
			// Для "Безлимит" дату-маркер не показываем: у бейджа уже есть
			// иконка бесконечности, а "31.12.9999" только путает
			if (!value || value.length < 10 || value.slice(0, 10) === '9999-12-31') return ''
			const [y, m, d] = value.slice(0, 10).split('-')
			return `${d}.${m}.${y}`
		}
	}
}
</script>

<template>
	<div class="card shadow-sm rounded-3 peerCard"
		 :id="'peer_'+Peer.id"
		:class="[{'border-warning': Peer.restricted}, cardPaymentClass]">
		<div>
			<div v-if="!Peer.restricted" class="card-header bg-transparent d-flex align-items-center gap-2 border-0">
				<div class="dot ms-0" :class="{active: Peer.status === 'running'}"></div>
				<div
					style="font-size: 0.8rem; color: #28a745"
					class="d-flex align-items-center"
					v-if="dashboardStore.Configuration.Server.dashboard_peer_list_display === 'list' && Peer.status === 'running'">
					<i class="bi bi-box-arrow-in-right me-2"></i>
					<span>
						{{ Peer.endpoint }}
					</span>
				</div>
				
				
				<div style="font-size: 0.8rem" class="ms-auto d-flex gap-2">
					<span class="text-primary">
						<i class="bi bi-arrow-down"></i><strong>
						{{(Peer.cumu_receive + Peer.total_receive).toFixed(4)}}</strong> GB
					</span>
					<span class="text-success">
						<i class="bi bi-arrow-up"></i><strong>
						{{(Peer.cumu_sent + Peer.total_sent).toFixed(4)}}</strong> GB
					</span>
					<span class="text-secondary" v-if="Peer.latest_handshake !== 'No Handshake'">
						<i class="bi bi-arrows-angle-contract"></i>
						{{getLatestHandshake}} ago
					</span>
				</div>
			</div>
			<div v-else class="border-0 card-header bg-transparent text-warning fw-bold" 
			     style="font-size: 0.8rem">
				<i class="bi-lock-fill me-2"></i>
				<LocaleText t="Access Restricted"></LocaleText>
			</div>
		</div>
		<div class="card-body pt-1" style="font-size: 0.9rem">
			<h6>
				{{Peer.name ? Peer.name : GetLocale('Untitled Peer')}}
			</h6>
			<div class="d-flex flex-wrap align-items-center gap-2 mb-1">
				<span class="badge rounded-pill" :class="paymentBadge.cls" v-if="Peer.PaymentStatus && Peer.PaymentStatus !== 'unset'"
					  :title="paymentTitle">
					<i class="bi me-1" :class="paymentBadge.icon"></i>
					{{paymentBadge.text}}
				</span>
				<span class="small text-muted"
					  v-if="paymentDate"
					  :title="GetLocale('Paid Until')">
					<i class="bi bi-calendar-event me-1"></i>{{paymentDate}}
				</span>
				<a v-if="Peer.telegram"
				   :href="'https://t.me/' + Peer.telegram.replace(/^@/, '')"
				   target="_blank"
				   rel="noopener noreferrer"
				   class="small text-decoration-none"
				   @click.stop>
					<i class="bi bi-telegram me-1"></i>{{Peer.telegram}}
				</a>
				<!--
					Продление прямо из карточки. Кнопка нужна, потому что
					истекающий пир иначе требует открывать настройки, а срок
					чаще всего продлевают именно в тот день, когда увидели
					жёлтую карточку.
				-->
				<span class="ms-auto d-flex align-items-center gap-1"
					  v-if="Peer.PaymentStatus === 'expiring' || Peer.PaymentStatus === 'expired'">
					<input type="number" min="1" max="3650"
						   class="form-control form-control-sm paymentExtendInput"
						   v-model.number="extendDays"
						   :title="GetLocale('Days')">
					<button class="btn btn-sm btn-success"
					        :disabled="!extendDays"
					        @click.stop="extendPayment()"
					        :title="GetLocale('Extend payment by N days')">
						<i class="bi bi-plus-lg"></i>
					</button>
				</span>
			</div>
			<div class="d-flex"
			     :class="[dashboardStore.Configuration.Server.dashboard_peer_list_display === 'grid' ? 'gap-1 flex-column' : 'flex-row gap-3']">
				<div :class="{'d-flex gap-2 align-items-center' : dashboardStore.Configuration.Server.dashboard_peer_list_display === 'list'}">
					<small class="text-muted">
						<LocaleText t="Public Key"></LocaleText>
					</small>
					<small class="d-block">
						<samp>{{Peer.id}}</samp>
					</small>
				</div>
				<div :class="{'d-flex gap-2 align-items-center' : dashboardStore.Configuration.Server.dashboard_peer_list_display === 'list'}">
					<small class="text-muted">
						<LocaleText t="Allowed IPs"></LocaleText>
					</small>
					<small class="d-block">
						<samp>{{Peer.allowed_ip}}</samp>
					</small>
				</div>
				<div class="d-flex align-items-center gap-1"
					:class="{'ms-auto': dashboardStore.Configuration.Server.dashboard_peer_list_display === 'list'}"
				>
					<PeerTagBadge :BackgroundColor="group.BackgroundColor" :GroupName="group.GroupName" :Icon="'bi-' + group.Icon"
						v-for="group in Object.values(ConfigurationInfo.Info.PeerGroups).filter(x => x.Peers.includes(Peer.id))"
					></PeerTagBadge>
					<div class="ms-auto px-2 rounded-3 subMenuBtn position-relative"
					     :class="{active: this.subMenuOpened}"
					>
						<a role="button" class="text-body"
						   @click="this.subMenuOpened = true">
							<h5 class="mb-0"><i class="bi bi-three-dots"></i></h5>
						</a>
						<Transition name="slide-fade">
							<PeerSettingsDropdown
								:dropup="getDropup"
								@qrcode="this.$emit('qrcode')"
								@configurationFile="this.$emit('configurationFile')"
								@setting="this.$emit('setting')"
								@jobs="this.$emit('jobs')"
								@refresh="this.$emit('refresh')"
								@share="this.$emit('share')"
								@assign="this.$emit('assign')"
								:Peer="Peer"
								:ConfigurationInfo="ConfigurationInfo"
								v-if="this.subMenuOpened"
								ref="target"
							></PeerSettingsDropdown>
						</Transition>
					</div>
				</div>
			</div>
		</div>
		<div class="card-footer" role="button" @click="$emit('details')" v-if="!this.Peer.restricted">
			<small class="d-flex align-items-center">
				<LocaleText t="Details"></LocaleText>
				<i class="bi bi-chevron-right ms-auto"></i>
			</small>
		</div>
		<div class="card-footer" v-else>
			<small class="d-flex align-items-center text-muted">
				<LocaleText t="Allow access to view details"></LocaleText>
			</small>
		</div>
	</div>
</template>

<style scoped>



.subMenuBtn.active{
	background-color: #ffffff20;
}

.peerCard{
	transition: box-shadow 0.1s cubic-bezier(0.82, 0.58, 0.17, 0.9);
}

.peerCard:hover{
	box-shadow: var(--bs-box-shadow) !important;
}

/*
  Подсветка по состоянию оплаты.

  Цвета фона заданы через rgb от --bs-warning / --bs-danger с небольшой
  прозрачностью: Bootstrap не даёт готового фона для warning/danger
  (есть только text-bg-* для текста), а заливка через --bs-warning-subtle
  в тёмной теме слишком тёмная и статус перестаёт читаться.

  Оттенок в rgb зашит намеренно: подстановка CSS-переменной внутрь
  rgb() без color-mix() не поддерживается, а color-mix не везде есть.
  Значения соответствуют Bootstrap 5.3 (warning #ffc107, danger #dc3545).
*/
.peer-card-expiring{
	border-color: var(--bs-warning) !important;
	border-width: 2px !important;
	background-color: rgba(255, 193, 7, 0.10);
}

.peer-card-overdue{
	border-color: var(--bs-danger) !important;
	border-width: 2px !important;
	background-color: rgba(220, 53, 69, 0.12);
}

/*
  Более плотный фон для тёмной темы: на тёмном фоне полупрозрачная
  заливка поверх тёмной подложки почти не видна.
*/
[data-bs-theme="dark"] .peer-card-expiring{
	background-color: rgba(255, 193, 7, 0.18);
}

[data-bs-theme="dark"] .peer-card-overdue{
	background-color: rgba(220, 53, 69, 0.22);
}

/* Поле продления на карточке не должно раздувать её по высоте */
.paymentExtendInput{
	width: 4.5rem;
}
</style>