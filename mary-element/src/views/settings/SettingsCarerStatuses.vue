<template>
  <GenericSettingsView
    title="Carer Employment Statuses"
    entityName="Carer Status"
    apiEndpoint="/carer-statuses"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
