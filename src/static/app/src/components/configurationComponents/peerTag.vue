<script setup lang="ts">
import {reactive, ref, watch} from "vue";
import LocaleText from "@/components/text/localeText.vue";
import bootstrapIcons from "bootstrap-icons/font/bootstrap-icons.json"

const predefinedColors = {
	"blue-100": "#cfe2ff",
	"blue-200": "#9ec5fe",
	"blue-300": "#6ea8fe",
	"blue-400": "#3d8bfd",
	"blue-500": "#0d6efd",
	"blue-600": "#0a58ca",
	"blue-700": "#084298",
	"blue-800": "#052c65",
	"blue-900": "#031633",
	"indigo-100": "#e0cffc",
	"indigo-200": "#c29ffa",
	"indigo-300": "#a370f7",
	"indigo-400": "#8540f5",
	"indigo-500": "#6610f2",
	"indigo-600": "#520dc2",
	"indigo-700": "#3d0a91",
	"indigo-800": "#290661",
	"indigo-900": "#140330",
	"purple-100": "#e2d9f3",
	"purple-200": "#c5b3e6",
	"purple-300": "#a98eda",
	"purple-400": "#8c68cd",
	"purple-500": "#6f42c1",
	"purple-600": "#59359a",
	"purple-700": "#432874",
	"purple-800": "#2c1a4d",
	"purple-900": "#160d27",
	"pink-100": "#f7d6e6",
	"pink-200": "#efadce",
	"pink-300": "#e685b5",
	"pink-400": "#de5c9d",
	"pink-500": "#d63384",
	"pink-600": "#ab296a",
	"pink-700": "#801f4f",
	"pink-800": "#561435",
	"pink-900": "#2b0a1a",
	"red-100": "#f8d7da",
	"red-200": "#f1aeb5",
	"red-300": "#ea868f",
	"red-400": "#e35d6a",
	"red-500": "#dc3545",
	"red-600": "#b02a37",
	"red-700": "#842029",
	"red-800": "#58151c",
	"red-900": "#2c0b0e",
	"orange-100": "#ffe5d0",
	"orange-200": "#fecba1",
	"orange-300": "#feb272",
	"orange-400": "#fd9843",
	"orange-500": "#fd7e14",
	"orange-600": "#ca6510",
	"orange-700": "#984c0c",
	"orange-800": "#653208",
	"orange-900": "#331904",
	"yellow-100": "#fff3cd",
	"yellow-200": "#ffe69c",
	"yellow-300": "#ffda6a",
	"yellow-400": "#ffcd39",
	"yellow-500": "#ffc107",
	"yellow-600": "#cc9a06",
	"yellow-700": "#997404",
	"yellow-800": "#664d03",
	"yellow-900": "#332701",
	"green-100": "#d1e7dd",
	"green-200": "#a3cfbb",
	"green-300": "#75b798",
	"green-400": "#479f76",
	"green-500": "#198754",
	"green-600": "#146c43",
	"green-700": "#0f5132",
	"green-800": "#0a3622",
	"green-900": "#051b11",
	"teal-100": "#d2f4ea",
	"teal-200": "#a6e9d5",
	"teal-300": "#79dfc1",
	"teal-400": "#4dd4ac",
	"teal-500": "#20c997",
	"teal-600": "#1aa179",
	"teal-700": "#13795b",
	"teal-800": "#0d503c",
	"teal-900": "#06281e",
	"cyan-100": "#cff4fc",
	"cyan-200": "#9eeaf9",
	"cyan-300": "#6edff6",
	"cyan-400": "#3dd5f3",
	"cyan-500": "#0dcaf0",
	"cyan-600": "#0aa2c0",
	"cyan-700": "#087990",
	"cyan-800": "#055160",
	"cyan-900": "#032830",
	"gray-100": "#f8f9fa",
	"gray-200": "#e9ecef",
	"gray-300": "#dee2e6",
	"gray-400": "#ced4da",
	"gray-500": "#adb5bd",
	"gray-600": "#6c757d",
	"gray-700": "#495057",
	"gray-800": "#343a40",
	"gray-900": "#212529",
	"white": "#fff",
	"black": "#000",
}
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js"
const store = WireguardConfigurationsStore()
const props = defineProps(['configuration'])
const groups = reactive({...props.configuration.Info.PeerGroups})
import { v4 } from "uuid"
import PeerTagSetting from "@/components/configurationComponents/peerTagComponents/peerTagSetting.vue";
import PeerTagIconPicker from "@/components/configurationComponents/peerTagComponents/peerTagIconPicker.vue";
import PeerTagColorPicker from "@/components/configurationComponents/peerTagComponents/peerTagColorPicker.vue";
import { fetchPost } from "@/utilities/fetch.js"

const addGroup = () => {
	groups[v4().toString()] = {
		GroupName: "",
		Description: "",
		BackgroundColor: randomColor(),
		Icon: randomIcon(),
		Peers: []
	}
}

const randomColor = () => {
	const keys = Object.keys(predefinedColors);
	const n = Math.floor(Math.random() * keys.length) + 1
	return predefinedColors[keys[n]]
}

const randomIcon = () => {
	const keys = Object.keys(bootstrapIcons)
	const n = Math.floor(Math.random() * keys.length) + 1
	return keys[n]
}

const iconPickerOpen = ref(false)
const colorPickerOpen = ref(false)
const selectedKey = ref("")
const emits = defineEmits(['close', 'update'])
watch(() => groups, (newVal) => {
	fetchPost("/api/updateWireguardConfigurationInfo", {
		Name: props.configuration.Name,
		Key: "PeerGroups",
		Value: newVal
	}, (res) => {
		if (res.status){
			emits('update', groups)
		}
	})
}, {
	deep: true
})

const edit = ref(false)
</script>

<template>
<div class="card shadow rounded-3" id="peerTag">
	<div class="card-header">
		<div class="form-check form-switch">
			<input class="form-check-input" type="checkbox" role="switch" id="showAllPeers" v-model="store.Filter.ShowAllPeersWhenHiddenTags">
			<label class="form-check-label" for="showAllPeers">
				<small>
					<LocaleText t="Show All Peers"></LocaleText>
				</small>
			</label>
		</div>
	</div>
	<div class="card-body p-2" >
		<Transition name="zoom" mode="out-in">
			<div v-if="!iconPickerOpen && !colorPickerOpen">
				<div v-if="Object.keys(groups).length === 0" class="text-center text-muted">
					<small><LocaleText t="No tag"></LocaleText></small>
				</div>
				<div class="d-flex flex-column gap-2" v-else>
					<TransitionGroup name="slide-fade">
						<PeerTagSetting v-for="(group, key) in groups"
										:groupId="key"
										@delete="delete groups[key]; store.Filter.HiddenTags = store.Filter.HiddenTags.filter(x => x !== key)"
										@colorPickerOpen="colorPickerOpen = true; selectedKey = key"
										@iconPickerOpen="iconPickerOpen = true; selectedKey = key"
										:key="key"
										:edit="edit"
										:group="group"></PeerTagSetting>
					</TransitionGroup>
				</div>
			</div>
			<PeerTagIconPicker
				v-else-if="iconPickerOpen"
				@close="iconPickerOpen = false"
				:group="groups[selectedKey]"></PeerTagIconPicker>
			<PeerTagColorPicker :colors="predefinedColors"
								@close="colorPickerOpen = false"
								:group="groups[selectedKey]"
								v-else-if="colorPickerOpen"></PeerTagColorPicker>
		</Transition>
	</div>
	<div class="card-footer p-2 d-flex gap-2" >
		<template v-if="!edit">
			<button
				@click="emits('close')"
				class="btn btn-sm bg-secondary-subtle text-secondary-emphasis border-secondary-subtle rounded-3">
				<small><LocaleText t="Close"></LocaleText></small>
			</button>
			<button
				@click="edit = true"
				class="btn btn-sm bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-3 ms-auto">
				<small><i class="bi bi-pen me-2"></i><LocaleText t="Edit"></LocaleText></small>
			</button>
		</template>
		<template v-else>

			<button
				@click="addGroup"
				class="btn btn-sm bg-primary-subtle text-primary-emphasis border-primary-subtle rounded-3 ">
				<small><i class="bi bi-plus-lg me-2"></i><LocaleText t="Tag"></LocaleText></small>
			</button>
			<button
				@click="edit = false"
				class="btn btn-sm bg-secondary-subtle text-secondary-emphasis border-secondary-subtle rounded-3 ms-auto">
				<small><LocaleText t="Done"></LocaleText></small>
			</button>
		</template>
	</div>
</div>
</template>

<style scoped>
#peerTag{
	width: 300px;
	position: absolute;
	right: 0;
	z-index: 9999;
	margin-top: 2px;
}
</style>