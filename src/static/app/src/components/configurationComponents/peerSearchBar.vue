<script setup>
import {GetLocale} from "@/utilities/locale.js";
import {computed, onMounted, ref, useTemplateRef} from "vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {onBeforeRouteUpdate, useRoute, useRouter} from "vue-router";

const searchBarPlaceholder = computed(() => {
	return GetLocale("Search Peers...")
})
let searchStringTimeout = undefined
const wireguardConfigurationStore = WireguardConfigurationsStore()
const searchString = ref(wireguardConfigurationStore.searchString)

const debounce = () => {
	if (!searchStringTimeout){
		searchStringTimeout = setTimeout(() => {
			wireguardConfigurationStore.searchString = searchString.value;
		}, 300)
	}else{
		clearTimeout(searchStringTimeout)
		searchStringTimeout = setTimeout(() => {
			wireguardConfigurationStore.searchString = searchString.value;
		}, 300)
	}
}

const emits = defineEmits(['close'])
const input = useTemplateRef('searchBar')
const props = defineProps(["ConfigurationInfo"])
const route = useRoute()
const router = useRouter()
if (route.query.peer){
	searchString.value = route.query.peer
	router.replace({ query: null })
}

const show = ref(true)
onMounted(() => {
	document.querySelector("#searchPeers").focus()
})

onBeforeRouteUpdate(() => {
	show.value = false
})

</script>

<template>
	<div class="fixed-bottom w-100 bottom-0 z-2 p-3" style="z-index: 1;" v-if="show">
		<div class="d-flex flex-column  searchPeersContainer ms-auto p-2 rounded-5"
			 style="width: 300px;">
			<div class="rounded-5 border border-white p-2 d-flex align-items-center gap-1 w-100">
				<input
					ref="searchBar"

					class="flex-grow-1 form-control form-control-sm rounded-5 bg-transparent border-0 border-secondary-subtle "
					:placeholder="searchBarPlaceholder"
					id="searchPeers"
					@keyup="debounce()"
					v-model="searchString">
			</div>
		</div>
	</div>
</template>

<style scoped>
.searchPeersContainer{
	backdrop-filter: blur(8px);
	width: 100%;
	background: linear-gradient(var(--degree), rgba(45, 173, 255, 0.4), rgba(255, 108, 109, 0.4), var(--brandColor2) 100%);
}
#searchPeers::placeholder{
	color: white;
}
</style>