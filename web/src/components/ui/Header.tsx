import { useAudioClip } from "@/hooks/useAudioClip";
import { Switcher } from "./Switcher";
import clsx from "clsx";

interface HeaderProps {
  devMode: boolean;
  setDevMode: (devMode: boolean) => void;
}

export const Header = ({ devMode, setDevMode }: HeaderProps) => {
  const playToggle = useAudioClip("/click.wav");

  return (
    <header className="flex w-full max-w-(--page-max-width) mx-auto mb-12 md:mb-8">
      <div className="grid grid-cols-12 gap-x-3">
        <div className="col-span-2 order-1 mb-8 md:mb-0">
          <div
            className={clsx(
              "relative top-[0.0875rem]",
              devMode && "cursor-pointer"
            )}
            onClick={() => {
              if (!devMode) {
                return;
              }

              playToggle();
              setDevMode(false);
            }}
          >
            <Logo />
          </div>
        </div>
        <div className="col-span-12 md:col-span-7 xl:col-span-6 order-3 md:order-2">
          <div className="text-balance">
            <div className="text-current/70 mb-3">
              Give your AI agent a voice. Powered by Kokoro TTS with 50+ voices
              across 9 languages.{" "}
            </div>
          </div>
        </div>
        <div className="col-span-10 md:col-span-3 xl:col-span-4 flex justify-end items-start order-2 md:order-3">
          <div className="relative -top-[0.57rem]">
            <Switcher
              checked={devMode}
              onChange={(checked) => setDevMode(checked)}
              id="dev-mode"
            />
          </div>
        </div>
      </div>
    </header>
  );
};

const Logo = () => {
  return (
    <span className="text-lg font-bold tracking-tight whitespace-nowrap">
      agent-fm
    </span>
  );
};
