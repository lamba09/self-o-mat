#ifndef SELF_O_MAT_ILOGICCONTROLLER_H
#define SELF_O_MAT_ILOGICCONTROLLER_H
#include <string>


namespace selfomat {
    namespace logic {
        class ILogicController {
        public:
            virtual bool trigger() = 0;
            virtual void acceptAgreement() = 0;
            // True only while the booth is still waiting for a print decision.
            virtual bool cancelPrint() = 0;
            virtual bool confirmPrint() = 0;
            virtual void stop() = 0;
            virtual bool getPrintConfirmationEnabled() = 0;
            virtual bool isAgreementVisible() = 0;
            virtual std::wstring getTranslation(std::string id) = 0;
        };
    }
}

#endif
