<template>
  <GenericSettingsView
    title="Carer Pension Schemes"
    entityName="Pension Scheme"
    apiEndpoint="/pension-schemes"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
