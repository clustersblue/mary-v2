<template>
  <GenericSettingsView
    title="Carer Employment References"
    entityName="Reference Type"
    apiEndpoint="/references"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
