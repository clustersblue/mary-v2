<template>
  <GenericSettingsView
    title="Requirement Verification Statuses"
    entityName="Requirement Status"
    apiEndpoint="/requirement-statuses"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
