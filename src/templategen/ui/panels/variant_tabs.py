"""VariantTabBar — switch between the template's variants."""

from PySide6.QtWidgets import QTabBar

from templategen.services.session import EditorSession


class VariantTabBar(QTabBar):
    def __init__(self, session: EditorSession) -> None:
        super().__init__()
        self._session = session
        self._suppress_signal = False

        self.setExpanding(False)

        session.template_changed.connect(self._rebuild)
        session.current_variant_changed.connect(self._on_session_changed)
        self.currentChanged.connect(self._on_user_changed)

        self._rebuild()

    def _rebuild(self) -> None:
        self._suppress_signal = True
        while self.count():
            self.removeTab(0)
        template = self._session.template
        if template is None:
            self.hide()
            self._suppress_signal = False
            return
        for i in range(len(template.variants)):
            self.addTab(f"Variant {i + 1}")
        self.setVisible(len(template.variants) > 1)
        self.setCurrentIndex(self._session.current_variant_index)
        self._suppress_signal = False

    def _on_session_changed(self, index: int) -> None:
        if self.currentIndex() == index:
            return
        self._suppress_signal = True
        self.setCurrentIndex(index)
        self._suppress_signal = False

    def _on_user_changed(self, index: int) -> None:
        if self._suppress_signal or index < 0:
            return
        self._session.set_current_variant_index(index)
