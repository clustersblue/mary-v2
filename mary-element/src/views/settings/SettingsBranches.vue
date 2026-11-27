<template>
  <GenericSettingsView
    title="Agency Branches Management"
    entityName="Branch"
    apiEndpoint="/branches"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
