class MailProfileEngine:
    def build_profile(self, folder, samples):
        return {
            "folder": folder,
            "sample_count": len(samples),
            "probable_sources": {
                "workorder": "unknown",
                "purchase_order": "unknown",
                "contact": "unknown",
                "location": "unknown",
            },
        }
