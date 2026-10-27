<script setup lang="ts">
import LocaleText from "@/components/text/localeText.vue";
import { fetchGet, fetchPost } from "@/utilities/fetch.js"
import {onMounted, ref, computed} from "vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const store = DashboardConfigurationStore();
const loaded = ref(false)
const data = ref<any>({})

const toggling = ref(false)
const savingSettings = ref(false)
const refreshing = ref(false)
const enabledSwitchEl = ref(null)

const adding = ref(false)
const newCidr = ref("")
const newComment = ref("")

// Локальная копия настроек для формы
const form = ref({
	list_size: "full",
	custom_url: "",
	auto_update: true,
	update_interval_hours: 6
})

// radio источника: builtin (list_size) или custom (custom_url)
const sourceMode = ref("builtin")

onMounted(async () => {
	await get()
})

const get = async () => {
	await fetchGet("/api/blocklist/get", {}, (res) => {
		data.value = res.data || {}
		form.value = {
			list_size: res.data.list_size || "full",
			custom_url: res.data.custom_url || "",
			auto_update: !!res.data.auto_update,
			update_interval_hours: res.data.update_interval_hours || 6
		}
		sourceMode.value = (res.data.custom_url || "").length > 0 ? "custom" : "builtin"
		loaded.value = true
	})
}

const toggle = async () => {
	toggling.value = true
	await fetchPost("/api/blocklist/toggle", {
		enabled: !data.value.enabled
	}, (res) => {
		if (res.status){
			store.newMessage("Blocklist",
				res.data?.enabled ? "Blocklist enabled" : "Blocklist disabled", "success")
		}else{
			store.newMessage("Blocklist", `Toggle failed: ${res.message}`, "danger")
		}
		if (res.data) data.value = res.data
		// Чекбокс кликнулся в DOM раньше ответа: при ошибке бэкенд оставил
		// enabled=false, но Vue не перепишет свойство (значение "не менялось")
		if (enabledSwitchEl.value){
			enabledSwitchEl.value.checked = !!data.value.enabled
		}
		toggling.value = false
	})
}

const saveSettings = async () => {
	savingSettings.value = true
	const body: any = {
		auto_update: form.value.auto_update,
		update_interval_hours: form.value.update_interval_hours
	}
	if (sourceMode.value === "builtin"){
		body.list_size = form.value.list_size
	}else{
		body.custom_url = form.value.custom_url
	}
	await fetchPost("/api/blocklist/settings", body, (res) => {
		if (res.status){
			store.newMessage("Blocklist", "Settings saved", "success")
		}else{
			store.newMessage("Blocklist", `Save failed: ${res.message}`, "danger")
		}
		if (res.data) data.value = res.data
		if (res.data){
			form.value = {
				list_size: res.data.list_size || "full",
				custom_url: res.data.custom_url || "",
				auto_update: !!res.data.auto_update,
				update_interval_hours: res.data.update_interval_hours || 6
			}
			sourceMode.value = (res.data.custom_url || "").length > 0 ? "custom" : "builtin"
		}
		savingSettings.value = false
	})
}

const refresh = async () => {
	refreshing.value = true
	await fetchPost("/api/blocklist/refresh", {}, (res) => {
		if (res.status){
			store.newMessage("Blocklist", "List refreshed", "success")
		}else{
			store.newMessage("Blocklist", `Refresh failed: ${res.message}`, "danger")
		}
		if (res.data) data.value = res.data
		refreshing.value = false
	})
}

const addEntry = async () => {
	if (newCidr.value.trim().length === 0){
		return
	}
	adding.value = true
	await fetchPost("/api/blocklist/entries/add", {
		cidr: newCidr.value.trim(),
		comment: newComment.value.trim()
	}, (res) => {
		if (res.status){
			store.newMessage("Blocklist", "Subnet added", "success")
			newCidr.value = ""
			newComment.value = ""
		}else{
			store.newMessage("Blocklist", `Add failed: ${res.message}`, "danger")
		}
		if (res.data) data.value = res.data
		adding.value = false
	})
}

const deleteEntry = async (cidr: string) => {
	await fetchPost("/api/blocklist/entries/delete", {
		cidr: cidr
	}, (res) => {
		if (res.status){
			store.newMessage("Blocklist", "Subnet removed", "success")
		}else{
			store.newMessage("Blocklist", `Delete failed: ${res.message}`, "danger")
		}
		if (res.data) data.value = res.data
	})
}

const totalSubnets = computed(() => {
	return (data.value.remote_count || 0) + (data.value.manual_count || 0)
})

const formatCounter = (c: any) => {
	const packets = c?.packets ?? 0
	const bytes = c?.bytes ?? 0
	if (packets === 0) return "—"
	const mb = bytes / (1024 * 1024)
	const sizeText = mb >= 1 ? `${mb.toFixed(1)} MB` : `${(bytes / 1024).toFixed(1)} KB`
	return `${packets.toLocaleString()} (${sizeText})`
}

// Перевод для атрибутов (placeholder), где LocaleText-компонент не работает
const t = (key: string) => {
	const locale: any = store.Locale
	if (locale && typeof locale[key] === "string" && locale[key].length > 0){
		return locale[key]
	}
	return key
}
</script>

<template>
	<div class="text-body w-100 h-100 pb-2 position-relative">
		<div class="w-100 h-100 card rounded-3">
			<div class="border-bottom z-0">
				<div class="d-flex text-body align-items-center sticky-top p-3 bg-body-tertiary rounded-top-3" style="border-top-right-radius: 0 !important;">
					<h6 class="my-2">
						<i class="bi bi-shield-fill-x me-2"></i>
						<LocaleText t="Blocklist"></LocaleText>
					</h6>
					<div class="form-check form-switch ms-auto my-2" v-if="loaded">
						<input class="form-check-input" type="checkbox" role="switch"
							   ref="enabledSwitchEl"
							   :checked="data.enabled"
							   :disabled="toggling"
							   @change="toggle()"
							   id="blocklistEnabled">
						<label class="form-check-label" for="blocklistEnabled">
							<LocaleText t="Enabled"></LocaleText>
						</label>
					</div>
				</div>
			</div>

			<div class="card-body d-flex flex-column gap-3" v-if="loaded">
				<div class="alert alert-warning mb-0" v-if="data.enabled && !data.applied">
					<i class="bi bi-exclamation-triangle-fill me-2"></i>
					<LocaleText t="Blocklist is enabled, but no rules are applied to nftables. Check that nft is installed and reload the rules"></LocaleText>
				</div>

				<!-- Статистика -->
				<div class="row g-3">
					<div class="col-12 col-md-6 col-xl-3">
						<div class="card h-100 rounded-3">
							<div class="card-body">
								<small class="text-muted">
									<LocaleText t="Blocked subnets"></LocaleText>
								</small>
								<h4 class="mb-0">{{ totalSubnets.toLocaleString() }}</h4>
								<small class="text-muted">
									{{ (data.remote_count || 0).toLocaleString() }}
									<LocaleText t="auto"></LocaleText>
									+
									{{ (data.manual_count || 0).toLocaleString() }}
									<LocaleText t="manual"></LocaleText>
								</small>
							</div>
						</div>
					</div>
					<div class="col-12 col-md-6 col-xl-3">
						<div class="card h-100 rounded-3">
							<div class="card-body">
								<small class="text-muted">
									<LocaleText t="Dropped (peers traffic)"></LocaleText>
								</small>
								<h4 class="mb-0" style="font-size: 1.1rem">{{ formatCounter(data.counters?.forward_block) }}</h4>
								<small class="text-muted">
									<LocaleText t="packets since last apply"></LocaleText>
								</small>
							</div>
						</div>
					</div>
					<div class="col-12 col-md-6 col-xl-3">
						<div class="card h-100 rounded-3">
							<div class="card-body">
								<small class="text-muted">
									<LocaleText t="Dropped (server traffic)"></LocaleText>
								</small>
								<h4 class="mb-0" style="font-size: 1.1rem">{{ formatCounter(data.counters?.output_block) }}</h4>
								<small class="text-muted">
									<LocaleText t="packets since last apply"></LocaleText>
								</small>
							</div>
						</div>
					</div>
					<div class="col-12 col-md-6 col-xl-3">
						<div class="card h-100 rounded-3">
							<div class="card-body">
								<small class="text-muted">
									<LocaleText t="Last update"></LocaleText>
								</small>
								<h4 class="mb-0" style="font-size: 1.1rem">
									{{ data.last_update || '—' }}</h4>
								<small class="text-muted" v-if="data.next_update">
									<LocaleText t="Next auto-update"></LocaleText>:
									{{ data.next_update }}
								</small>
							</div>
						</div>
					</div>
				</div>

				<!-- Настройки -->
				<div class="card rounded-3">
					<div class="card-header bg-transparent border-bottom">
						<h6 class="my-2">
							<i class="bi bi-gear-fill me-2"></i>
							<LocaleText t="Blocklist Settings"></LocaleText>
						</h6>
					</div>
					<div class="card-body d-flex flex-column gap-3">
						<div>
							<label class="text-muted mb-1 d-block">
								<strong><small><LocaleText t="List Source"></LocaleText></small></strong>
							</label>
							<div class="form-check">
								<input class="form-check-input" type="radio" name="blocklistSource"
									   id="blocklistSourceLite" value="lite"
									   v-model="form.list_size" :disabled="sourceMode === 'custom'">
								<label class="form-check-label" for="blocklistSourceLite">
									<LocaleText t="Built-in lite list (about 1291 subnets)"></LocaleText>
								</label>
							</div>
							<div class="form-check">
								<input class="form-check-input" type="radio" name="blocklistSource"
									   id="blocklistSourceFull" value="full"
									   v-model="form.list_size" :disabled="sourceMode === 'custom'">
								<label class="form-check-label" for="blocklistSourceFull">
									<LocaleText t="Built-in full list (about 12895 subnets)"></LocaleText>
								</label>
							</div>
							<div class="form-check">
								<input class="form-check-input" type="radio" name="blocklistSource"
									   id="blocklistSourceCustom" value="custom"
									   v-model="sourceMode">
								<label class="form-check-label" for="blocklistSourceCustom">
									<LocaleText t="Custom URL"></LocaleText>
								</label>
							</div>
							<div class="mt-2" v-if="sourceMode === 'custom'">
								<input type="text" class="form-control rounded-3"
									   v-model="form.custom_url"
									   :placeholder="'https://example.com/list.json'">
								<small class="text-muted">
									<LocaleText t="Supported: AmneziaVPN ip-list.json (hostname/ip fields) or plain text, one subnet per line"></LocaleText>
								</small>
							</div>
						</div>

						<div class="d-flex align-items-center gap-3 flex-wrap">
							<div class="form-check form-switch mb-0">
								<input class="form-check-input" type="checkbox" role="switch"
									   v-model="form.auto_update" id="blocklistAutoUpdate">
								<label class="form-check-label" for="blocklistAutoUpdate">
									<LocaleText t="Auto update"></LocaleText>
								</label>
							</div>
							<div class="d-flex align-items-center gap-2" v-if="form.auto_update">
								<label class="text-muted mb-0">
									<small><LocaleText t="Update interval"></LocaleText></small>
								</label>
								<select class="form-select form-select-sm rounded-3 w-auto"
										v-model="form.update_interval_hours">
									<option :value="1">1 <LocaleText t="hours"></LocaleText></option>
									<option :value="3">3 <LocaleText t="hours"></LocaleText></option>
									<option :value="6">6 <LocaleText t="hours"></LocaleText></option>
									<option :value="12">12 <LocaleText t="hours"></LocaleText></option>
									<option :value="24">24 <LocaleText t="hours"></LocaleText></option>
									<option :value="72">72 <LocaleText t="hours"></LocaleText></option>
								</select>
							</div>
						</div>

						<div class="d-flex gap-2">
							<button class="btn btn-primary rounded-3 shadow-sm"
									@click="saveSettings()" :disabled="savingSettings">
								<span class="spinner-border spinner-border-sm me-2" v-if="savingSettings"></span>
								<i class="bi bi-save me-2" v-else></i>
								<LocaleText t="Save settings"></LocaleText>
							</button>
							<button class="btn btn-outline-secondary rounded-3 shadow-sm"
									@click="refresh()" :disabled="refreshing">
								<span class="spinner-border spinner-border-sm me-2" v-if="refreshing"></span>
								<i class="bi bi-arrow-repeat me-2" v-else></i>
								<LocaleText t="Refresh list now"></LocaleText>
							</button>
						</div>
					</div>
				</div>

				<!-- Ручные записи -->
				<div class="card rounded-3">
					<div class="card-header bg-transparent border-bottom">
						<h6 class="my-2">
							<i class="bi bi-pencil-fill me-2"></i>
							<LocaleText t="Manual entries"></LocaleText>
						</h6>
					</div>
					<div class="card-body d-flex flex-column gap-3">
						<form @submit="(e) => { e.preventDefault(); addEntry() }"
							  class="d-flex gap-2 flex-wrap">
							<input type="text" class="form-control rounded-3 w-auto flex-grow-1"
								   style="min-width: 220px"
								   v-model="newCidr"
								   placeholder="1.2.3.4/24">
							<input type="text" class="form-control rounded-3 w-auto flex-grow-1"
								   style="min-width: 180px"
								   v-model="newComment"
								   :placeholder="t('Comment (optional)')">
							<button class="btn btn-sm bg-primary-subtle text-primary-emphasis border-1 border-primary-subtle rounded-3 shadow-sm"
									type="submit" :disabled="adding">
								<i class="bi bi-plus-circle-fill me-2"></i>
								<LocaleText t="Add"></LocaleText>
							</button>
						</form>
						<small class="text-muted">
							<LocaleText t="Manual entries are always merged with the auto-updated list and survive list updates"></LocaleText>
						</small>

						<div class="table-responsive" v-if="(data.manual_entries || []).length > 0">
							<table class="table table-hover align-middle">
								<thead>
								<tr>
									<th scope="col"><LocaleText t="Subnet"></LocaleText></th>
									<th scope="col"><LocaleText t="Comment"></LocaleText></th>
									<th scope="col"><LocaleText t="Added"></LocaleText></th>
									<th scope="col"></th>
								</tr>
								</thead>
								<tbody>
								<tr v-for="entry in data.manual_entries" :key="entry.cidr">
									<td><code>{{ entry.cidr }}</code></td>
									<td>{{ entry.comment || '—' }}</td>
									<td>{{ entry.created || '—' }}</td>
									<td class="text-end">
										<button class="btn btn-sm btn-outline-danger rounded-3"
												@click="deleteEntry(entry.cidr)">
											<i class="bi bi-trash3-fill"></i>
										</button>
									</td>
								</tr>
								</tbody>
							</table>
						</div>
						<div class="text-muted text-center py-2" v-else>
							<i class="bi bi-inboxes me-2"></i>
							<LocaleText t="No manual entries yet"></LocaleText>
						</div>
					</div>
				</div>
			</div>

			<div class="card-body" v-else>
				<div class="d-flex align-items-center gap-2 text-muted">
					<span class="spinner-border spinner-border-sm"></span>
					<LocaleText t="Loading..."></LocaleText>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>
